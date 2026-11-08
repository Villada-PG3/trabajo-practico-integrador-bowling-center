import calendar
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.http import urlencode
from django.views import View
from django.views.generic import CreateView, DetailView, FormView, TemplateView

from .forms import (
    AgregarJugadorForm,
    AgregarProductoForm,
    BuscarReservaForm,
    ReservaForm,
    TirarForm,
)
from .models import (
    Cliente,
    Jugador,
    Lanzamiento,
    Participacion,
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
    # Pagina de inicio del sitio publico.

    template_name = "myapp/home.html"

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        # La seccion "Pistas" del home muestra las pistas reales cargadas.
        contexto["pistas"] = Pista.objects.filter(
            disponible=True
        )
        return contexto


class ReservaView(CreateView):
    # GET: muestra el formulario de reserva vacio.
    # POST: valida el formulario, crea el Cliente y guarda la Reserva en
    # estado pendiente_a_pago.
    # Es un CreateView porque el objetivo de la vista es crear una Reserva.

    model = Reserva
    form_class = ReservaForm
    template_name = "myapp/reserva.html"
    success_url = reverse_lazy("myapp:reserva")

    def valor(self, nombre):
        # Los datos elegidos viajan en la URL mientras el cliente navega y en
        # el POST cuando confirma la reserva.
        if self.request.method == "POST":
            return self.request.POST.get(nombre, "")
        return self.request.GET.get(nombre, "")

    def url_paso(self, paso, pista, anio, mes, dia=None, hora="", duracion=None):
        # Arma el enlace de un paso llevando lo que ya se eligio.
        datos = {"paso": paso}

        if pista is not None:
            datos["pista"] = pista.numero_pista
        if dia is not None:
            datos["dia"] = dia.isoformat()
        if hora:
            datos["hora"] = hora
        if duracion:
            datos["duracion"] = duracion

        datos["anio"] = anio
        datos["mes"] = mes

        return reverse("myapp:reserva") + "?" + urlencode(datos)

    def calcular_duracion(self, pista, hora):
        # Si el cliente no eligio duracion se ofrece la minima de la pista.
        if pista is None or not hora:
            return None

        minima = int(pista.obtenerDuracionMinima() * 60)
        pedida = self.valor("duracion")

        if pedida.isdigit() and minima <= int(pedida) <= 240:
            return int(pedida)

        return minima

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)

        pistas = Pista.objects.filter(disponible=True)
        pista = pistas.filter(numero_pista=self.valor("pista") or 0).first()

        dia = None
        if self.valor("dia"):
            try:
                dia = date.fromisoformat(self.valor("dia"))
            except ValueError:
                dia = None

        hoy = date.today()
        anio = int(self.valor("anio") or (dia.year if dia else hoy.year))
        mes = int(self.valor("mes") or (dia.month if dia else hoy.month))

        if mes < 1 or mes > 12:
            anio, mes = hoy.year, hoy.month

        disponibilidad = calcular_disponibilidad(anio, mes)

        hora = self.valor("hora")[:5]
        duracion = self.calcular_duracion(pista, hora)
        hora_fin = ""

        if duracion:
            hora_fin = sumar_minutos(hora, duracion)

        slots = []
        horarios_libres = 0

        if dia is not None:
            info = disponibilidad["dias"].get(dia.isoformat())

            if info:
                for slot in info["slots"]:
                    if slot["libres"] > 0:
                        horarios_libres += 1
                    slot["url"] = self.url_paso(3, pista, anio, mes, dia, slot["hora"])
                    slots.append(slot)

        # El paso lo decide la URL; si el formulario volvio con errores se
        # muestra el paso 4, que es donde se confirma la reserva.
        paso = 4 if self.request.method == "POST" else int(self.valor("paso") or 1)

        if paso < 1 or paso > 4:
            paso = 1
        if pista is None:
            paso = 1
        elif paso > 2 and (dia is None or not hora):
            paso = 2

        opciones = []

        if pista is not None and hora:
            minima = int(pista.obtenerDuracionMinima() * 60)

            for minutos in range(minima, minima + 181, 30):
                fin = sumar_minutos(hora, minutos)

                if not fin:
                    break

                opciones.append(
                    {
                        "minutos": minutos,
                        "fin": fin,
                        "texto": texto_duracion(minutos),
                        "elegido": minutos == duracion,
                        "url": self.url_paso(3, pista, anio, mes, dia, hora, minutos),
                    }
                )

        total = None

        if pista is not None and duracion:
            total = pista.obtenerPrecioHora() * Decimal(duracion) / Decimal("60")

        nombre_dia = ""
        if dia is not None:
            nombre_dia = (
                f"{NOMBRES_DIA[dia.weekday()]} {dia.day} "
                f"de {NOMBRES_MES[dia.month - 1]}"
            )

        anio_anterior, mes_anterior = anio, mes - 1
        if mes == 1:
            anio_anterior, mes_anterior = anio - 1, 12

        anio_siguiente, mes_siguiente = anio, mes + 1
        if mes == 12:
            anio_siguiente, mes_siguiente = anio + 1, 1

        semanas = armar_semanas(
            anio,
            mes,
            disponibilidad["dias"],
            dia,
            pista.numero_pista if pista else "",
        )

        nodos = []
        for numero in range(1, 5):
            if numero < paso:
                estado = "done"
            elif numero == paso:
                estado = "active"
            else:
                estado = "pending"

            nodos.append(
                {
                    "numero": numero,
                    "titulo": TITULOS_PASO[numero],
                    "detalle": DETALLES_PASO[numero],
                    "estado": estado,
                    "url": self.url_paso(
                        numero, pista, anio, mes, dia, hora, duracion
                    ),
                }
            )

        contexto["pistas"] = pistas
        contexto["paso"] = paso
        contexto["titulo_paso"] = f"Paso {paso} de 4: {TITULOS_PASO[paso]}"
        contexto["progreso"] = paso * 25
        contexto["nodos"] = nodos

        contexto["pista_elegida"] = pista
        contexto["dia_elegido"] = dia
        contexto["nombre_dia"] = nombre_dia
        contexto["hora_elegida"] = hora
        contexto["hora_fin_texto"] = hora_fin
        contexto["duracion_elegida"] = duracion
        contexto["duracion_texto"] = texto_duracion(duracion) if duracion else ""
        contexto["opciones_duracion"] = opciones

        contexto["anio"] = anio
        contexto["mes"] = mes
        contexto["nombre_mes"] = f"{NOMBRES_MES[mes - 1]} {anio}"
        contexto["mes_anterior"] = mes_anterior
        contexto["mes_anterior_anio"] = anio_anterior
        contexto["mes_siguiente"] = mes_siguiente
        contexto["mes_siguiente_anio"] = anio_siguiente

        contexto["semanas"] = semanas
        contexto["slots"] = slots
        contexto["horarios_libres"] = horarios_libres
        contexto["total_pistas"] = disponibilidad["total_pistas"]
        contexto["jugadores_texto"] = contexto["form"]["cantidad_jugadores"].value() or 4
        contexto["total_estimado"] = total

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
        # Pasa los errores de Reserva.clean() al formulario, para que se vean
        # al lado del campo que corresponde (pista, fecha, hora_fin, etc.) y
        # no como un error 500.
        for campo, mensajes in error.message_dict.items():
            if campo not in form.fields:
                campo = None  # errores generales -> arriba del formulario
            for mensaje in mensajes:
                form.add_error(campo, mensaje)


# Cada cuanto tiempo se puede empezar una reserva: 30 minutos.
PASO_MINUTOS = 30

NOMBRES_MES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]
NOMBRES_DIA = [
    "lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo",
]
TITULOS_PASO = {
    1: "Seleccion de pista",
    2: "Dia y horario",
    3: "Horario y duracion",
    4: "Tus datos",
}
DETALLES_PASO = {
    1: "Tipo y tarifa",
    2: "Calendario",
    3: "Duracion",
    4: "Datos",
}


def texto_duracion(minutos):
    # Convierte 90 en "1 h 30 min", para mostrar en pantalla.
    horas = minutos // 60
    resto = minutos % 60

    if horas == 0:
        return f"{resto} min"
    if resto == 0:
        return f"{horas} h"
    return f"{horas} h {resto} min"


def sumar_minutos(hora, minutos):
    # Devuelve la hora de fin, o "" si la reserva se pasaria de las 24 hs.
    partes = hora.split(":")
    total = int(partes[0]) * 60 + int(partes[1]) + minutos

    if total >= 24 * 60:
        return ""

    return f"{total // 60:02d}:{total % 60:02d}"


def armar_semanas(anio, mes, dias, dia_elegido, numero_pista):
    # Arma la grilla del calendario: filas de 7 dias que arrancan el lunes.
    primer_dia = date(anio, mes, 1)
    arranque = primer_dia - timedelta(days=primer_dia.weekday())

    semanas = []
    semana = []

    for numero in range(42):
        fecha = arranque + timedelta(days=numero)

        if fecha.month != mes:
            semana.append({"numero": fecha.day, "estado": "fuera", "elegido": False})
        else:
            info = dias[fecha.isoformat()]
            con_lugar = 0

            for slot in info["slots"]:
                if slot["libres"] > 0:
                    con_lugar += 1

            semana.append(
                {
                    "numero": fecha.day,
                    "estado": info["estado"],
                    "elegido": fecha == dia_elegido,
                    "titulo": f"{con_lugar} horarios con lugar",
                    "url": reverse("myapp:reserva")
                    + "?"
                    + urlencode(
                        {
                            "paso": 2,
                            "pista": numero_pista,
                            "anio": anio,
                            "mes": mes,
                            "dia": fecha.isoformat(),
                        }
                    ),
                }
            )

        if len(semana) == 7:
            semanas.append(semana)
            semana = []

    # Si la ultima fila es toda del mes siguiente, no se muestra.
    while semanas:
        fila_afuera = True

        for dia in semanas[-1]:
            if dia["estado"] != "fuera":
                fila_afuera = False

        if not fila_afuera:
            break

        semanas.pop()

    return semanas


def minutos_de(hora):
    # Convierte una hora (10:30) en minutos desde la medianoche (630).
    return hora.hour * 60 + hora.minute


def calcular_disponibilidad(anio, mes):
    # Arma el mapa de ocupacion del mes, dia por dia y franja por franja.
    # Para cada dia devuelve:
    # estado: libre (ninguna reserva), parcial (algunas), completo (todas
    # las pistas tomadas), cerrado (no hay horario ese dia) o
    # pasado (ya paso).
    # slots:  las franjas de 30 minutos con cuantas pistas quedan libres.
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

    # Si el dia es hoy, los horarios que ya pasaron no se ofrecen.
    momento = timezone.localtime()
    minutos_ahora = momento.hour * 60 + momento.minute

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
                if fecha == hoy and desde < minutos_ahora:
                    desde += PASO_MINUTOS
                    continue

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

        todas_libres = True
        todas_ocupadas = True

        for slot in slots:
            if slot["libres"] != slot["total"]:
                todas_libres = False
            if slot["libres"] != 0:
                todas_ocupadas = False

        if todas_libres:
            estado = "libre"
        elif todas_ocupadas:
            estado = "completo"
        else:
            estado = "parcial"

        dias[clave] = {"estado": estado, "slots": slots}

    return {"anio": anio, "mes": mes, "total_pistas": total_pistas, "dias": dias}


class ConsultaReservaView(FormView):
    # El cliente busca su reserva con el codigo.

    template_name = "myapp/consulta_reserva.html"
    form_class = BuscarReservaForm

    def form_valid(self, form):
        return redirect(
            "myapp:detalle_reserva", codigo=form.cleaned_data["codigo"]
        )


class DetalleReservaView(DetailView):
    # Muestra la reserva completa a partir del codigo.

    model = Reserva
    template_name = "myapp/detalle_reserva.html"
    context_object_name = "reserva"
    slug_field = "codigo"
    slug_url_kwarg = "codigo"

    def get_queryset(self):
        return super().get_queryset()

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["productos"] = Producto.objects.all()
        contexto["pedidos"] = self.object.pedidos.all()
        return contexto


class CancelarReservaView(View):
    # Cancela una reserva pendiente de pago que todavia no empezo.

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
    # Suma un producto de la cafeteria a la reserva del cliente.

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

        pedido.agregarDetalle(producto, cantidad)
        messages.success(request, f"Agregado: {cantidad} x {producto.nombre}.")

        return redirect("myapp:detalle_reserva", codigo=reserva.codigo)


def obtener_partida(reserva):
    # Devuelve la partida de la reserva; si no tiene, crea la primera.
    partida = reserva.partidas.first()

    if partida is None:
        partida = Partida.objects.create(
            reserva=reserva,
            numero=1,
            fecha_hora_inicio=timezone.make_aware(
                datetime.combine(reserva.fecha, reserva.hora_inicio)
            ),
            estado=EstadoPartida.objects.get(nombre="pendiente"),
        )

    return partida


class PartidaView(DetailView):
    # Pantalla para cargar los tiros de la partida.

    model = Reserva
    template_name = "myapp/partida.html"
    context_object_name = "reserva"
    slug_field = "codigo"
    slug_url_kwarg = "codigo"

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        partida = obtener_partida(self.object)

        jugadores = []
        for participacion in partida.participaciones.all():
            jugadores.append(
                {
                    "participacion": participacion,
                    "nombre": participacion.jugador.nombre,
                    "total": participacion.calcularPuntajeTotal(),
                    "marcas": participacion.marcasPorFrame(),
                    "siguiente": participacion.siguienteTiro(),
                }
            )

        terminada = bool(jugadores)

        for jugador in jugadores:
            if jugador["siguiente"] is not None:
                terminada = False
                break


        contexto["partida"] = partida
        contexto["jugadores"] = jugadores
        contexto["terminada"] = terminada
        contexto["ganador"] = partida.obtenerGanador() if terminada else None
        return contexto


class TirarView(View):
    # Carga un lanzamiento del jugador en el proximo turno que le toca.

    def post(self, request, codigo):
        reserva = get_object_or_404(Reserva, codigo=codigo.upper())
        partida = obtener_partida(reserva)

        participacion = Participacion.objects.filter(
            pk=request.POST.get("participacion"), partida=partida
        ).first()

        if participacion is None:
            messages.error(request, "No encontramos ese jugador en la partida.")
            return redirect("myapp:partida", codigo=reserva.codigo)

        form = TirarForm(request.POST)

        if not form.is_valid():
            messages.error(request, "Pone cuantos pinos derribo (0 a 10).")
            return redirect("myapp:partida", codigo=reserva.codigo)

        pinos = form.cleaned_data["pinos"]

        turno = participacion.siguienteTiro()

        if turno is None:
            messages.info(
                request, f"{participacion.jugador.nombre} ya termino la partida."
            )
            return redirect("myapp:partida", codigo=reserva.codigo)

        try:
            Lanzamiento.objects.create(
                participacion=participacion,
                numero_frame=turno[0],
                numero_lanzamiento=turno[1],
                pinos_derribados=pinos,
            )
        except ValidationError as error:
            mensajes = " ".join(
                texto for lista in error.message_dict.values() for texto in lista
            )
            messages.error(request, f"No se pudo cargar el tiro: {mensajes}")
            return redirect("myapp:partida", codigo=reserva.codigo)

        messages.success(
            request,
            f"{participacion.jugador.nombre}: tirado {pinos} en el frame "
            f"{turno[0]}.",
        )
        self.actualizar_estado(partida)

        return redirect("myapp:partida", codigo=reserva.codigo)

    def actualizar_estado(self, partida):
        # Pasa la partida a en_curso y a finalizada cuando todos terminaron.
        participaciones = list(partida.participaciones.all())

        if not participaciones:
            return

        todos_terminaron = True

        for participacion in participaciones:
            if participacion.siguienteTiro() is not None:
                todos_terminaron = False
                break

        if todos_terminaron:
            nombre = "finalizada"
        else:
            nombre = "en_curso"
        if partida.estado.nombre != nombre:
            partida.estado = EstadoPartida.objects.get(nombre=nombre)
            partida.save()


class AgregarJugadorJuegoView(View):
    # Suma un jugador a la partida de la reserva.

    def post(self, request, codigo):
        reserva = get_object_or_404(Reserva, codigo=codigo.upper())
        partida = obtener_partida(reserva)

        form = AgregarJugadorForm(request.POST)

        if not form.is_valid():
            messages.error(request, "Escribi el nombre del jugador.")
            return redirect("myapp:partida", codigo=reserva.codigo)

        nombre = form.cleaned_data["nombre"]

        jugador = Jugador.objects.create(nombre=nombre)

        try:
            partida.agregarJugador(jugador)
        except ValidationError as error:
            jugador.delete()
            messages.error(request, error.message)
        else:
            messages.success(request, f"Se sumo {nombre} a la partida.")

        return redirect("myapp:partida", codigo=reserva.codigo)
