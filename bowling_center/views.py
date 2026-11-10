import calendar
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import ProtectedError
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    FormView,
    ListView,
    TemplateView,
    UpdateView,
)

from .forms import (
    AgregarJugadorForm,
    AgregarProductoForm,
    BuscarReservaForm,
    ClienteForm,
    HorarioAtencionForm,
    PedidoOperacionForm,
    PistaForm,
    ProductoForm,
    ReservaForm,
    TirarForm,
    TipoPistaForm,
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
    TipoPista,
)


class HomeView(TemplateView):
    # Pagina de inicio del sitio publico.

    template_name = "bowling_center/home.html"

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        # La seccion "Pistas" del home muestra las pistas reales cargadas.
        contexto["pistas"] = Pista.objects.filter(
            disponible=True
        )
        return contexto


class StaffAuthenticationForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update(
            {"class": "form-control", "autocomplete": "username"}
        )
        self.fields["password"].widget.attrs.update(
            {"class": "form-control", "autocomplete": "current-password"}
        )

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)

        if not user.is_staff:
            raise ValidationError(
                "Esta pantalla es exclusiva para el personal del centro."
            )


class OperacionLoginView(LoginView):
    authentication_form = StaffAuthenticationForm
    template_name = "bowling_center/operacion_login.html"
    redirect_authenticated_user = True
    next_page = reverse_lazy("bowling_center:gestion")


class OperacionLogoutView(LogoutView):
    next_page = reverse_lazy("bowling_center:home")


class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    login_url = reverse_lazy("bowling_center:operacion_login")

    def test_func(self):
        return self.request.user.is_staff


class GestionPanelView(StaffRequiredMixin, TemplateView):
    template_name = "bowling_center/gestion_panel.html"

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["cantidad_pistas"] = Pista.objects.count()
        contexto["cantidad_tipos"] = TipoPista.objects.count()
        contexto["cantidad_horarios"] = HorarioAtencion.objects.count()
        contexto["cantidad_productos"] = Producto.objects.count()
        contexto["cantidad_clientes"] = Cliente.objects.count()
        return contexto


class GestionTiposPistaView(StaffRequiredMixin, ListView):
    model = TipoPista
    template_name = "bowling_center/gestion_tipos.html"
    context_object_name = "tipos"
    queryset = TipoPista.objects.order_by("nombre")


class GestionPistasView(StaffRequiredMixin, ListView):
    model = Pista
    template_name = "bowling_center/gestion_pistas.html"
    context_object_name = "pistas"
    queryset = Pista.objects.order_by("numero_pista")


class GestionHorariosView(StaffRequiredMixin, ListView):
    model = HorarioAtencion
    template_name = "bowling_center/gestion_horarios.html"
    context_object_name = "horarios"
    queryset = HorarioAtencion.objects.all()


class GestionProductosView(StaffRequiredMixin, ListView):
    model = Producto
    template_name = "bowling_center/gestion_productos.html"
    context_object_name = "productos"
    queryset = Producto.objects.order_by("tipo", "nombre")


class GestionClientesView(StaffRequiredMixin, ListView):
    model = Cliente
    template_name = "bowling_center/gestion_clientes.html"
    context_object_name = "clientes"
    queryset = Cliente.objects.order_by("nombre")


class GestionCreateView(StaffRequiredMixin, CreateView):
    template_name = "bowling_center/gestion_form.html"
    page_title = ""
    page_description = ""
    list_url_name = ""

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["titulo"] = self.page_title
        contexto["descripcion"] = self.page_description
        contexto["volver_url"] = reverse(f"bowling_center:{self.list_url_name}")
        return contexto

    def form_valid(self, form):
        messages.success(self.request, f"{self.object_label} creado correctamente.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse(f"bowling_center:{self.list_url_name}")


class GestionUpdateView(StaffRequiredMixin, UpdateView):
    template_name = "bowling_center/gestion_form.html"
    page_title = ""
    page_description = ""
    list_url_name = ""

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["titulo"] = self.page_title
        contexto["descripcion"] = self.page_description
        contexto["volver_url"] = reverse(f"bowling_center:{self.list_url_name}")
        return contexto

    def form_valid(self, form):
        messages.success(self.request, f"{self.object_label} actualizado correctamente.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse(f"bowling_center:{self.list_url_name}")


class GestionDeleteView(StaffRequiredMixin, DeleteView):
    template_name = "bowling_center/gestion_confirm_delete.html"
    page_title = ""
    list_url_name = ""

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["titulo"] = self.page_title
        contexto["volver_url"] = reverse(f"bowling_center:{self.list_url_name}")
        return contexto

    def get_success_url(self):
        return reverse(f"bowling_center:{self.list_url_name}")

    def form_valid(self, form):
        nombre = str(self.object)
        try:
            self.object.delete()
        except ProtectedError:
            messages.error(
                self.request,
                f"No se puede eliminar {nombre} porque todavía está en uso.",
            )
        else:
            messages.success(self.request, f"{nombre} se eliminó correctamente.")
        return HttpResponseRedirect(self.get_success_url())


class CrearTipoPistaView(GestionCreateView):
    model = TipoPista
    form_class = TipoPistaForm
    object_label = "El tipo de pista"
    page_title = "Nuevo tipo de pista"
    page_description = "Definí el precio, la capacidad y la duración mínima."
    list_url_name = "gestion_tipos"
    success_url = reverse_lazy("bowling_center:gestion_tipos")


class EditarTipoPistaView(GestionUpdateView):
    model = TipoPista
    form_class = TipoPistaForm
    object_label = "El tipo de pista"
    page_title = "Editar tipo de pista"
    page_description = "Actualizá las características de este tipo de pista."
    list_url_name = "gestion_tipos"
    success_url = reverse_lazy("bowling_center:gestion_tipos")


class EliminarTipoPistaView(GestionDeleteView):
    model = TipoPista
    page_title = "Eliminar tipo de pista"
    list_url_name = "gestion_tipos"
    success_url = reverse_lazy("bowling_center:gestion_tipos")


class CrearPistaView(GestionCreateView):
    model = Pista
    form_class = PistaForm
    object_label = "La pista"
    page_title = "Nueva pista"
    page_description = "Elegí el tipo y definí si la pista estará disponible."
    list_url_name = "gestion_pistas"
    success_url = reverse_lazy("bowling_center:gestion_pistas")


class EditarPistaView(GestionUpdateView):
    model = Pista
    form_class = PistaForm
    object_label = "La pista"
    page_title = "Editar pista"
    page_description = "Actualizá el tipo, la tarifa o la disponibilidad."
    list_url_name = "gestion_pistas"
    success_url = reverse_lazy("bowling_center:gestion_pistas")


class EliminarPistaView(GestionDeleteView):
    model = Pista
    page_title = "Eliminar pista"
    list_url_name = "gestion_pistas"
    success_url = reverse_lazy("bowling_center:gestion_pistas")


class CrearHorarioView(GestionCreateView):
    model = HorarioAtencion
    form_class = HorarioAtencionForm
    object_label = "El horario"
    page_title = "Nuevo horario de atención"
    page_description = "Agregá una franja de apertura para el centro."
    list_url_name = "gestion_horarios"
    success_url = reverse_lazy("bowling_center:gestion_horarios")


class EditarHorarioView(GestionUpdateView):
    model = HorarioAtencion
    form_class = HorarioAtencionForm
    object_label = "El horario"
    page_title = "Editar horario de atención"
    page_description = "Modificá el día o la franja horaria."
    list_url_name = "gestion_horarios"
    success_url = reverse_lazy("bowling_center:gestion_horarios")


class EliminarHorarioView(GestionDeleteView):
    model = HorarioAtencion
    page_title = "Eliminar horario de atención"
    list_url_name = "gestion_horarios"
    success_url = reverse_lazy("bowling_center:gestion_horarios")


class CrearProductoView(GestionCreateView):
    model = Producto
    form_class = ProductoForm
    object_label = "El producto"
    page_title = "Nuevo producto"
    page_description = "Agregá una comida o bebida al catálogo de cafetería."
    list_url_name = "gestion_productos"
    success_url = reverse_lazy("bowling_center:gestion_productos")


class EditarProductoView(GestionUpdateView):
    model = Producto
    form_class = ProductoForm
    object_label = "El producto"
    page_title = "Editar producto"
    page_description = "Actualizá el nombre, la categoría o el precio de venta."
    list_url_name = "gestion_productos"
    success_url = reverse_lazy("bowling_center:gestion_productos")


class EliminarProductoView(GestionDeleteView):      
    model = Producto
    page_title = "Eliminar producto"
    list_url_name = "gestion_productos"
    success_url = reverse_lazy("bowling_center:gestion_productos")


class CrearClienteView(GestionCreateView):
    model = Cliente
    form_class = ClienteForm
    object_label = "El cliente"
    page_title = "Nuevo cliente"
    page_description = "Cargá los datos del cliente."
    list_url_name = "gestion_clientes"
    success_url = reverse_lazy("bowling_center:gestion_clientes")


class EditarClienteView(GestionUpdateView):
    model = Cliente
    form_class = ClienteForm
    object_label = "El cliente"
    page_title = "Editar cliente"
    page_description = "Actualizá los datos del cliente."
    list_url_name = "gestion_clientes"
    success_url = reverse_lazy("bowling_center:gestion_clientes")


class EliminarClienteView(GestionDeleteView):
    model = Cliente
    page_title = "Eliminar cliente"
    list_url_name = "gestion_clientes"
    success_url = reverse_lazy("bowling_center:gestion_clientes")


def _fecha_hora_reserva(fecha, hora):
    return timezone.make_aware(
        datetime.combine(fecha, hora),
        timezone.get_current_timezone(),
    )


def obtener_estado_pistas(ahora=None):
    momento = timezone.localtime(ahora or timezone.now())
    hasta = momento + timedelta(minutes=60)
    fechas = {momento.date(), hasta.date()}
    reservas_por_pista = {}

    reservas = (
        Reserva.objects.filter(fecha__in=fechas)
        .exclude(estado__nombre="cancelada")
        .order_by("fecha", "hora_inicio")
    )
    for reserva in reservas:
        reservas_por_pista.setdefault(reserva.pista_id, []).append(reserva)

    pistas = Pista.objects.order_by("numero_pista")
    resultado = []

    for pista in pistas:
        reservas = reservas_por_pista.get(pista.pk, [])
        activa = next(
            (
                reserva
                for reserva in reservas
                if _fecha_hora_reserva(reserva.fecha, reserva.hora_inicio)
                <= momento
                < _fecha_hora_reserva(reserva.fecha, reserva.hora_fin)
            ),
            None,
        )
        proxima = next(
            (
                reserva
                for reserva in reservas
                if momento
                < _fecha_hora_reserva(reserva.fecha, reserva.hora_inicio)
                <= hasta
            ),
            None,
        )

        if not pista.disponible:
            estado = "mantenimiento"
            reserva = None
        elif activa and activa.estado.nombre in {
            "en_curso",
            "pagada",
            "finalizada",
        }:
            estado = "ocupada"
            reserva = activa
        elif activa:
            estado = "reservada"
            reserva = activa
        elif proxima:
            estado = "reservada"
            reserva = proxima
        else:
            estado = "libre"
            reserva = None

        puede_checkin = bool(
            reserva
            and reserva.estado.nombre == "pendiente_a_pago"
            and activa == reserva
        )
        puede_marcar_ausencia = bool(
            puede_checkin
            and momento
            >= _fecha_hora_reserva(reserva.fecha, reserva.hora_inicio)
            + timedelta(minutes=15)
        )
        resultado.append(
            {
                "pista": pista,
                "estado": estado,
                "reserva": reserva,
                "puede_checkin": puede_checkin,
                "puede_marcar_ausencia": puede_marcar_ausencia,
            }
        )

    return resultado


class OperacionMapaView(StaffRequiredMixin, TemplateView):
    template_name = "bowling_center/operacion_mapa.html"

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["pistas"] = obtener_estado_pistas()
        contexto["ahora"] = timezone.localtime()
        return contexto


class OperacionReservasView(StaffRequiredMixin, TemplateView):
    template_name = "bowling_center/operacion_reservas.html"

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        hoy = timezone.localdate()
        fecha_parametro = self.request.GET.get("fecha", "")

        try:
            fecha = date.fromisoformat(fecha_parametro) if fecha_parametro else hoy
        except ValueError:
            fecha = hoy
            messages.error(self.request, "La fecha indicada no es válida.")

        cliente = self.request.GET.get("cliente", "").strip()
        reservas = (
            Reserva.objects.filter(fecha=fecha)
            .order_by("hora_inicio", "pista__numero_pista")
        )
        if cliente:
            reservas = reservas.filter(cliente__nombre__icontains=cliente)

        ahora = timezone.localtime()
        reservas = list(reservas)
        for reserva in reservas:
            reserva.puede_registrar_llegada = (
                reserva.estado.nombre == "pendiente_a_pago"
                and _fecha_hora_reserva(reserva.fecha, reserva.hora_inicio)
                <= ahora
                < _fecha_hora_reserva(reserva.fecha, reserva.hora_fin)
            )
            reserva.puede_marcar_ausencia = (
                reserva.estado.nombre == "pendiente_a_pago"
                and _fecha_hora_reserva(reserva.fecha, reserva.hora_inicio)
                + timedelta(minutes=15)
                <= ahora
                < _fecha_hora_reserva(reserva.fecha, reserva.hora_fin)
            )

        contexto["reservas"] = reservas
        contexto["fecha"] = fecha
        contexto["fecha_hoy"] = hoy
        contexto["cliente_busqueda"] = cliente
        contexto["ahora"] = ahora
        contexto["productos_comida"] = Producto.objects.filter(
            tipo=Producto.COMIDA
        ).order_by("nombre")
        contexto["productos_bebida"] = Producto.objects.filter(
            tipo=Producto.BEBIDA
        ).order_by("nombre")
        return contexto


class OperacionReservaActionView(StaffRequiredMixin, View):
    def get_reserva(self, codigo):
        return get_object_or_404(
            Reserva.objects.all(),
            codigo=codigo.upper(),
        )

    def volver_al_mapa(self):
        return redirect("bowling_center:operacion")


class CheckInReservaView(OperacionReservaActionView):
    def post(self, request, codigo):
        reserva = self.get_reserva(codigo)
        ahora = timezone.localtime()
        inicio = _fecha_hora_reserva(reserva.fecha, reserva.hora_inicio)
        fin = _fecha_hora_reserva(reserva.fecha, reserva.hora_fin)

        if (
            reserva.estado.nombre != "pendiente_a_pago"
            or not reserva.pista.disponible
            or not inicio <= ahora < fin
        ):
            messages.error(
                request,
                "Solo se puede registrar la llegada durante una reserva "
                "pendiente y vigente.",
            )
        else:
            reserva.estado = EstadoReserva.objects.get(nombre="en_curso")
            reserva.save()
            messages.success(
                request,
                f"Se registró la llegada de {reserva.cliente.nombre}.",
            )

        return self.volver_al_mapa()


class NoShowReservaView(OperacionReservaActionView):
    def post(self, request, codigo):
        reserva = self.get_reserva(codigo)
        ahora = timezone.localtime()
        inicio = _fecha_hora_reserva(reserva.fecha, reserva.hora_inicio)
        fin = _fecha_hora_reserva(reserva.fecha, reserva.hora_fin)

        if (
            reserva.estado.nombre != "pendiente_a_pago"
            or not reserva.pista.disponible
            or ahora < inicio + timedelta(minutes=15)
            or ahora >= fin
        ):
            messages.error(
                request,
                "La reserva solo se puede marcar como ausente 15 minutos "
                "después del inicio y mientras siga vigente.",
            )
        else:
            reserva.estado = EstadoReserva.objects.get(nombre="cancelada")
            reserva.save()
            messages.success(
                request,
                f"La reserva de {reserva.cliente.nombre} quedó cancelada; "
                "la pista está libre.",
            )

        return self.volver_al_mapa()


class CambiarDisponibilidadPistaView(StaffRequiredMixin, View):
    def post(self, request, pista_id):
        pista = get_object_or_404(Pista, pk=pista_id)
        disponible = request.POST.get("disponible") == "1"

        if not disponible:
            hoy = timezone.localdate()
            tiene_reservas = (
                Reserva.objects.filter(
                    pista=pista,
                    fecha__gte=hoy,
                )
                .exclude(estado__nombre="cancelada")
                .exists()
            )
            if tiene_reservas:
                messages.error(
                    request,
                    "No se puede poner la pista en mantenimiento porque "
                    "tiene reservas vigentes o futuras.",
                )
                return redirect("bowling_center:operacion")

        pista.disponible = disponible
        pista.save(update_fields=["disponible"])
        if disponible:
            messages.success(request, f"La pista {pista.numero_pista} está disponible.")
        else:
            messages.success(
                request,
                f"La pista {pista.numero_pista} quedó en mantenimiento.",
            )
        return redirect("bowling_center:operacion")


class AgregarPedidoOperacionView(StaffRequiredMixin, View):
    def post(self, request, codigo):
        reserva = get_object_or_404(
            Reserva.objects.all(),
            codigo=codigo.upper(),
        )
        fecha = request.POST.get("fecha", "")
        cliente = request.POST.get("cliente", "")
        form = PedidoOperacionForm(request.POST)
        volver = reverse("bowling_center:operacion_reservas")
        parametros = []

        if fecha:
            parametros.append(f"fecha={fecha}")
        if cliente:
            parametros.append(f"cliente={cliente}")
        if parametros:
            volver = volver + "?" + "&".join(parametros)

        if not form.is_valid():
            messages.error(request, "Elegí un producto y una cantidad válida.")
            return redirect(volver)

        if reserva.estado.nombre not in {"pendiente_a_pago", "en_curso"}:
            messages.error(
                request,
                "Solo se pueden agregar consumos a una reserva pendiente "
                "o en curso.",
            )
            return redirect(volver)

        estado_abierto = EstadoPedido.objects.get(nombre="abierto")
        pedido, _ = Pedido.objects.get_or_create(
            reserva=reserva,
            estado=estado_abierto,
        )
        producto = form.cleaned_data["producto"]
        pedido.agregarDetalle(producto, form.cleaned_data["cantidad"])
        messages.success(
            request,
            f"Se agregó {form.cleaned_data['cantidad']} × {producto.nombre} "
            f"a la reserva {reserva.codigo}.",
        )
        return redirect(volver)


class CajaReservaView(StaffRequiredMixin, DetailView):
    model = Reserva
    template_name = "bowling_center/operacion_caja.html"
    context_object_name = "reserva"
    slug_field = "codigo"
    slug_url_kwarg = "codigo"

    def get_queryset(self):
        return (
            super()
            .get_queryset()
        )


class CerrarPedidoView(StaffRequiredMixin, View):
    def post(self, request, codigo, pedido_id):
        reserva = get_object_or_404(Reserva, codigo=codigo.upper())
        pedido = get_object_or_404(Pedido, pk=pedido_id, reserva=reserva)

        if (
            pedido.estado.nombre == "abierto"
            and reserva.estado.nombre != "cancelada"
        ):
            pedido.cerrar()
            messages.success(request, f"El pedido #{pedido.pk} quedó cerrado.")
        else:
            messages.error(
                request,
                "Ese pedido ya está cerrado o la reserva está cancelada.",
            )

        return redirect("bowling_center:caja", codigo=reserva.codigo)


class MarcarReservaPagadaView(StaffRequiredMixin, View):
    def post(self, request, codigo):
        reserva = get_object_or_404(Reserva, codigo=codigo.upper())

        if reserva.estado.nombre in {"pendiente_a_pago", "en_curso"}:
            reserva.estado = EstadoReserva.objects.get(nombre="pagada")
            reserva.save()
            messages.success(request, "La reserva quedó marcada como pagada.")
        else:
            messages.error(
                request, "No se puede marcar como pagada en su estado actual."
            )

        return redirect("bowling_center:caja", codigo=reserva.codigo)


class FinalizarReservaView(StaffRequiredMixin, View):
    def post(self, request, codigo):
        reserva = get_object_or_404(Reserva, codigo=codigo.upper())

        if reserva.estado.nombre == "pagada":
            reserva.estado = EstadoReserva.objects.get(nombre="finalizada")
            reserva.save()
            messages.success(request, "La reserva quedó finalizada.")
        else:
            messages.error(
                request,
                "Para finalizar una reserva primero debe estar pagada.",
            )

        return redirect("bowling_center:caja", codigo=reserva.codigo)


class ReservaView(CreateView):
    # GET: muestra el formulario de reserva vacio.
    # POST: valida el formulario, crea el Cliente y guarda la Reserva en
    # estado pendiente_a_pago.
    # Es un CreateView porque el objetivo de la vista es crear una Reserva.

    model = Reserva
    form_class = ReservaForm
    template_name = "bowling_center/reserva.html"
    success_url = reverse_lazy("bowling_center:reserva")

    def valor(self, nombre):
        # Los datos elegidos viajan en la URL mientras el cliente navega y en
        # el POST cuando confirma la reserva.
        if self.request.method == "POST":
            return self.request.POST.get(nombre, "")
        return self.request.GET.get(nombre, "")

    def url_paso(self, paso, pista, anio, mes, dia=None, hora="", duracion=None):
        # Arma el enlace de un paso llevando lo que ya se eligio.
        url = f"{reverse('bowling_center:reserva')}?paso={paso}"

        if pista is not None:
            url += f"&pista={pista.numero_pista}"
        if dia is not None:
            url += f"&dia={dia.isoformat()}"
        if hora:
            url += f"&hora={hora}"
        if duracion:
            url += f"&duracion={duracion}"

        return url + f"&anio={anio}&mes={mes}"

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
            "bowling_center:detalle_reserva", kwargs={"codigo": self.object.codigo}
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
                    "url": (
                        f"{reverse('bowling_center:reserva')}?paso=2"
                        f"&pista={numero_pista}&anio={anio}&mes={mes}"
                        f"&dia={fecha.isoformat()}"
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

        franjas_del_dia = []

        for franja in franjas:
            if franja.dia_semana == fecha.weekday():
                franjas_del_dia.append(franja)

        if not franjas_del_dia or total_pistas == 0:
            dias[clave] = {"estado": "cerrado", "slots": []}
            continue

        reservas_del_dia = []

        for reserva in reservas:
            if reserva["fecha"] == fecha:
                reservas_del_dia.append(reserva)

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

    template_name = "bowling_center/consulta_reserva.html"
    form_class = BuscarReservaForm

    def form_valid(self, form):
        return redirect(
            "bowling_center:detalle_reserva", codigo=form.cleaned_data["codigo"]
        )


class DetalleReservaView(DetailView):
    # Muestra la reserva completa a partir del codigo.

    model = Reserva
    template_name = "bowling_center/detalle_reserva.html"
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

        return redirect("bowling_center:detalle_reserva", codigo=reserva.codigo)


class AgregarPedidoView(View):
    # Suma un producto de la cafeteria a la reserva del cliente.

    def post(self, request, codigo):
        reserva = get_object_or_404(Reserva, codigo=codigo.upper())
        form = AgregarProductoForm(request.POST)

        if not form.is_valid():
            messages.error(
                request, "Revisa la cantidad: tiene que ser entre 1 y 20."
            )
            return redirect("bowling_center:detalle_reserva", codigo=reserva.codigo)

        if not reserva.sePuedePedir():
            messages.error(
                request, "Esta reserva esta cancelada: no se pueden pedir cosas."
            )
            return redirect("bowling_center:detalle_reserva", codigo=reserva.codigo)

        # Si la reserva ya tiene un pedido abierto se usa ese; si no, se abre.
        estado_abierto = EstadoPedido.objects.get(nombre="abierto")
        pedido, _ = Pedido.objects.get_or_create(
            reserva=reserva, estado=estado_abierto
        )

        producto = form.cleaned_data["producto"]
        cantidad = form.cleaned_data["cantidad"]

        pedido.agregarDetalle(producto, cantidad)
        messages.success(request, f"Agregado: {cantidad} x {producto.nombre}.")

        return redirect("bowling_center:detalle_reserva", codigo=reserva.codigo)


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
    template_name = "bowling_center/partida.html"
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
            return redirect("bowling_center:partida", codigo=reserva.codigo)

        form = TirarForm(request.POST)

        if not form.is_valid():
            messages.error(request, "Pone cuantos pinos derribo (0 a 10).")
            return redirect("bowling_center:partida", codigo=reserva.codigo)

        pinos = form.cleaned_data["pinos"]

        turno = participacion.siguienteTiro()

        if turno is None:
            messages.info(
                request, f"{participacion.jugador.nombre} ya termino la partida."
            )
            return redirect("bowling_center:partida", codigo=reserva.codigo)

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
            return redirect("bowling_center:partida", codigo=reserva.codigo)

        messages.success(
            request,
            f"{participacion.jugador.nombre}: tirado {pinos} en el frame "
            f"{turno[0]}.",
        )
        self.actualizar_estado(partida)

        return redirect("bowling_center:partida", codigo=reserva.codigo)

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

        if (
            partida.estado.nombre != "pendiente"
            or partida.participaciones.filter(
                lanzamientos__isnull=False
            ).exists()
        ):
            messages.error(
                request,
                "La partida ya empezó. Los jugadores se agregan antes "
                "del primer tiro.",
            )
            return redirect("bowling_center:partida", codigo=reserva.codigo)

        form = AgregarJugadorForm(request.POST)

        if not form.is_valid():
            messages.error(request, "Escribi el nombre del jugador.")
            return redirect("bowling_center:partida", codigo=reserva.codigo)

        nombre = form.cleaned_data["nombre"]

        jugador = Jugador.objects.create(nombre=nombre)

        try:
            partida.agregarJugador(jugador)
        except ValidationError as error:
            jugador.delete()
            messages.error(request, error.message)
        else:
            messages.success(request, f"Se sumo {nombre} a la partida.")

        return redirect("bowling_center:partida", codigo=reserva.codigo)
