import calendar
from datetime import date, datetime, time

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DetailView, FormView, TemplateView

from .forms import AgregarProductoForm, BuscarReservaForm, ReservaForm
from .models import (
    Cliente,
    EstadoPartida,
    EstadoPedido,
    EstadoReserva,
    HorarioAtencion,
    Partida,
    Pedido,
    Pista,
    Producto,
    Reserva,
)


class HomeView(TemplateView):
    """Pagina de inicio del sitio publico."""

    template_name = "myapp/home.html"

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        # La seccion "Pistas" del home muestra las pistas reales cargadas.
        contexto["pistas"] = Pista.objects.filter(
            disponible=True
        ).select_related("tipo_pista")
        return contexto


class ReservaView(CreateView):
    """
    GET: muestra el formulario de reserva vacio.
    POST: valida el formulario, crea el Cliente y guarda la Reserva en
    estado pendiente_a_pago.

    Es un CreateView porque el objetivo de la vista es crear una Reserva.
    """

    model = Reserva
    form_class = ReservaForm
    template_name = "myapp/reserva.html"
    success_url = reverse_lazy("myapp:reserva")

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        # Las pistas se muestran como tarjetas en el paso 1 del formulario.
        contexto["pistas"] = Pista.objects.filter(
            disponible=True
        ).select_related("tipo_pista")
        # Dias de la semana en los que el centro atiende (0 = lunes).
        # El calendario del paso 2 deshabilita los demas.
        contexto["dias_abiertos"] = list(
            HorarioAtencion.objects.values_list("dia_semana", flat=True).distinct()
        )
        return contexto

    def form_valid(self, form):
        try:
            # Todo junto: si la reserva no pasa las validaciones del modelo,
            # no queda un cliente suelto en la base.
            with transaction.atomic():
                # Si el email ya existe se reusa el cliente y se actualizan
                # sus datos con los del formulario.
                cliente, creado = Cliente.objects.get_or_create(
                    email=form.cleaned_data["email"],
                    defaults={
                        "nombre": form.cleaned_data["nombre"],
                        "direccion": form.cleaned_data["direccion"],
                        "telefono": form.cleaned_data["telefono"],
                    },
                )

                if not creado:
                    cliente.nombre = form.cleaned_data["nombre"]
                    cliente.direccion = form.cleaned_data["direccion"]
                    cliente.telefono = form.cleaned_data["telefono"]
                    cliente.save()

                reserva = form.save(commit=False)
                reserva.cliente = cliente
                # El estado inicial NO lo pone el modelo: lo decide la vista.
                reserva.estado = EstadoReserva.objects.get(
                    nombre="pendiente_a_pago"
                )
                # Reserva.save() ejecuta full_clean(): aca se validan horario
                # de atencion, duracion minima, capacidad y superposicion, y
                # se congela el precio de la pista.
                reserva.save()

                # El enunciado pide que cada reserva registre como minimo
                # una partida: se crea la partida 1, pendiente de empezar.
                Partida.objects.create(
                    reserva=reserva,
                    numero=1,
                    fecha_hora_inicio=timezone.make_aware(
                        datetime.combine(reserva.fecha, reserva.hora_inicio)
                    ),
                    estado=EstadoPartida.objects.get(nombre="pendiente"),
                )
        except ValidationError as error:
            self.agregar_errores_de_la_reserva(form, error)
            return self.form_invalid(form)

        self.object = reserva
        messages.success(
            self.request,
            "Reserva confirmada. Tu codigo es "
            f"{reserva.codigo}. Pista {reserva.pista.numero_pista} el "
            f"{reserva.fecha} de {reserva.hora_inicio:%H:%M} a "
            f"{reserva.hora_fin:%H:%M}. Queda pendiente de pago.",
        )
        return super().form_valid(form)

    def get_success_url(self):
        # Despues de reservar mostramos el detalle, con el codigo bien visible.
        return reverse(
            "myapp:detalle_reserva", kwargs={"codigo": self.object.codigo}
        )

    def agregar_errores_de_la_reserva(self, form, error):
        """
        Pasa los errores de Reserva.clean() al formulario, para que se vean
        al lado del campo que corresponde (pista, fecha, hora_fin, etc.) y
        no como un error 500.
        """
        for campo, mensajes in error.message_dict.items():
            if campo not in form.fields:
                campo = None  # errores generales -> arriba del formulario
            for mensaje in mensajes:
                form.add_error(campo, mensaje)


# Cada cuanto tiempo se puede empezar una reserva: 30 minutos.
PASO_MINUTOS = 30


def minutos_de(hora):
    """Convierte una hora (10:30) en minutos desde la medianoche (630)."""
    return hora.hour * 60 + hora.minute


def calcular_disponibilidad(anio, mes):
    """
    Arma el mapa de ocupacion del mes, dia por dia y franja por franja.

    Para cada dia devuelve:
      estado: libre (ninguna reserva), parcial (algunas), completo (todas
              las pistas tomadas), cerrado (no hay horario ese dia) o
              pasado (ya paso).
      slots:  las franjas de 30 minutos con cuantas pistas quedan libres.
    """
    pistas = Pista.objects.filter(disponible=True)
    total_pistas = pistas.count()

    franjas = list(HorarioAtencion.objects.all())

    dias_del_mes = calendar.monthrange(anio, mes)[1]
    primer_dia = date(anio, mes, 1)
    ultimo_dia = date(anio, mes, dias_del_mes)

    # Todas las reservas del mes que ocupan pista (las canceladas no cuentan).
    reservas = list(
        Reserva.objects.filter(
            fecha__gte=primer_dia, fecha__lte=ultimo_dia
        )
        .exclude(estado__nombre="cancelada")
        .values("fecha", "hora_inicio", "hora_fin")
    )
    for reserva in reservas:
        reserva["desde"] = minutos_de(reserva["hora_inicio"])
        reserva["hasta"] = minutos_de(reserva["hora_fin"])

    hoy = date.today()
    dias = {}

    for numero_dia in range(1, dias_del_mes + 1):
        fecha = date(anio, mes, numero_dia)
        clave = fecha.isoformat()

        if fecha < hoy:
            dias[clave] = {"estado": "pasado", "slots": []}
            continue

        franjas_del_dia = [f for f in franjas if f.dia_semana == fecha.weekday()]
        if not franjas_del_dia or total_pistas == 0:
            dias[clave] = {"estado": "cerrado", "slots": []}
            continue

        reservas_del_dia = [r for r in reservas if r["fecha"] == fecha]
        slots = []

        for franja in franjas_del_dia:
            desde = minutos_de(franja.hora_apertura)
            hasta = minutos_de(franja.hora_cierre)

            # Se ofrecen horarios de arranque cada 30 minutos.
            while desde + PASO_MINUTOS <= hasta:
                fin_slot = desde + PASO_MINUTOS
                ocupadas = 0

                for reserva in reservas_del_dia:
                    if reserva["desde"] < fin_slot and reserva["hasta"] > desde:
                        ocupadas += 1

                slots.append(
                    {
                        "hora": time(desde // 60, desde % 60).strftime("%H:%M"),
                        "libres": max(total_pistas - ocupadas, 0),
                        "total": total_pistas,
                    }
                )
                desde += PASO_MINUTOS

        if all(slot["libres"] == slot["total"] for slot in slots):
            estado = "libre"
        elif all(slot["libres"] == 0 for slot in slots):
            estado = "completo"
        else:
            estado = "parcial"

        dias[clave] = {"estado": estado, "slots": slots}

    return {"anio": anio, "mes": mes, "total_pistas": total_pistas, "dias": dias}


class DisponibilidadView(View):
    """Devuelve el mapa de disponibilidad de un mes en JSON (para el calendario)."""

    def get(self, request):
        hoy = date.today()

        try:
            anio = int(request.GET.get("anio", hoy.year))
            mes = int(request.GET.get("mes", hoy.month))
        except (TypeError, ValueError):
            return JsonResponse({"error": "anio y mes tienen que ser numeros"}, status=400)

        if mes < 1 or mes > 12 or anio < 2000 or anio > 2100:
            return JsonResponse({"error": "mes o anio fuera de rango"}, status=400)

        return JsonResponse(calcular_disponibilidad(anio, mes))


class ConsultaReservaView(FormView):
    """El cliente busca su reserva con el codigo."""

    template_name = "myapp/consulta_reserva.html"
    form_class = BuscarReservaForm

    def form_valid(self, form):
        return redirect(
            "myapp:detalle_reserva", codigo=form.cleaned_data["codigo"]
        )


class DetalleReservaView(DetailView):
    """Muestra la reserva completa a partir del codigo."""

    model = Reserva
    template_name = "myapp/detalle_reserva.html"
    context_object_name = "reserva"
    slug_field = "codigo"
    slug_url_kwarg = "codigo"

    def get_queryset(self):
        return super().get_queryset().select_related(
            "cliente", "pista__tipo_pista", "estado"
        )

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["productos"] = Producto.objects.all()
        contexto["pedidos"] = self.object.pedidos.prefetch_related(
            "detalles__producto"
        ).select_related("estado")
        return contexto


class CancelarReservaView(View):
    """Cancela una reserva pendiente de pago que todavia no empezo."""

    def post(self, request, codigo):
        reserva = get_object_or_404(Reserva, codigo=codigo.upper())

        if reserva.sePuedeCancelar():
            reserva.estado = EstadoReserva.objects.get(nombre="cancelada")
            reserva.save()
            messages.success(
                request, "La reserva quedo cancelada y la pista quedo libre."
            )
        else:
            messages.error(
                request,
                "Esta reserva no se puede cancelar: ya empezo o no esta "
                "pendiente de pago.",
            )

        return redirect("myapp:detalle_reserva", codigo=reserva.codigo)


class AgregarPedidoView(View):
    """Suma un producto de la cafeteria a la reserva del cliente."""

    def post(self, request, codigo):
        reserva = get_object_or_404(Reserva, codigo=codigo.upper())
        form = AgregarProductoForm(request.POST)

        if not form.is_valid():
            messages.error(
                request, "Revisa la cantidad: tiene que ser entre 1 y 20."
            )
            return redirect("myapp:detalle_reserva", codigo=reserva.codigo)

        if not reserva.sePuedePedir():
            messages.error(
                request, "Esta reserva esta cancelada: no se pueden pedir cosas."
            )
            return redirect("myapp:detalle_reserva", codigo=reserva.codigo)

        # Si la reserva ya tiene un pedido abierto se usa ese; si no, se abre.
        estado_abierto = EstadoPedido.objects.get(nombre="abierto")
        pedido, _ = Pedido.objects.get_or_create(
            reserva=reserva, estado=estado_abierto
        )

        producto = form.cleaned_data["producto"]
        cantidad = form.cleaned_data["cantidad"]

        try:
            pedido.agregarDetalle(producto, cantidad)
        except ValidationError as error:
            messages.error(request, f"No se pudo agregar: {error.message}")
        else:
            messages.success(
                request, f"Agregado: {cantidad} x {producto.nombre}."
            )

        return redirect("myapp:detalle_reserva", codigo=reserva.codigo)
