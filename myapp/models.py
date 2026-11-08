import secrets
from datetime import datetime
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models, transaction
from django.utils import timezone

# Modelos de Tipo y Estado
# TipoPista: los tipos de pista que ofrece el centro (chica, mediana, grande, vip...).
# Cada tipo define el precio por hora, cuantos jugadores entran y la duracion minima.
class TipoPista(models.Model):
    id_tipo_pista = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=20, unique=True)
    descripcion = models.TextField(blank=True)
    precio_hora = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))]
    )
    capacidad_maxima = models.PositiveIntegerField(
        validators=[MinValueValidator(1)]
    )
    duracion_minima = models.PositiveIntegerField(
        validators=[MinValueValidator(1)]
    )

    def __str__(self):
        return self.nombre

# EstadoReserva: los estados posibles de una reserva (pendiente_a_pago, pagada, cancelada...).
# Esta en una tabla aparte para que no se escriba cualquier texto a mano.
class EstadoReserva(models.Model):
    id_estado_reserva = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=50, unique=True)
    descripcion = models.TextField(blank=True)

    def __str__(self):
        return self.nombre

# EstadoPedido: los estados del pedido de la confiteria (abierto, cerrado, cancelado).
class EstadoPedido(models.Model):
    id_estado_pedido = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.nombre

# EstadoPartida: los estados de la partida de bowling (en_curso, finalizada).
class EstadoPartida(models.Model):
    id_estado_partida = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.nombre

# Cliente: la persona que reserva. Se carga en el momento de la reserva,
# no hay registro de usuarios. El email es unico para no duplicar clientes.
class Cliente(models.Model):
    id_cliente = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    direccion = models.CharField(max_length=200)
    telefono = models.CharField(max_length=30)
    email = models.EmailField(max_length=100, unique=True)

    def __str__(self):
        return self.nombre

# Jugador: el que juega la partida. Puede estar asociado a un cliente o no,
# porque tambien puede venir alguien suelto que no reservo.
class Jugador(models.Model):
    id_jugador = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    cliente = models.OneToOneField(
        Cliente,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="Jugador"
    )

    def esCliente(self):
        return self.cliente is not None

    def __str__(self):
        return self.nombre

# Pista: cada pista fisica del bowling. Toma el precio, la capacidad y la duracion
# minima del tipo de pista, pero puede tener su propio precio si el centro quiere.
class Pista(models.Model):
    numero_pista = models.AutoField(primary_key=True)
    precio_hora = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    disponible  = models.BooleanField(default=True)
    tipo_pista = models.ForeignKey(
        TipoPista,
        on_delete=models.PROTECT,
        related_name="pistas"
    )

    def obtenerCapacidadMaxima(self):
        return self.tipo_pista.capacidad_maxima

    def obtenerPrecioHora(self):
        return self.precio_hora or self.tipo_pista.precio_hora

    def obtenerDuracionMinima(self):
        return self.tipo_pista.duracion_minima

    def estaDisponible(self, fecha, inicio, fin):
        reservas = Reserva.objects.filter(
            pista=self,
            fecha=fecha,
            hora_inicio__lt=fin,
            hora_fin__gt=inicio
        ).exclude(estado__nombre="cancelada")

        return not reservas.exists()

    def __str__(self):
        return f"Pista {self.numero_pista}"

# Letras y numeros sin los que se confunden al leerlos (0/O, 1/I).
CODIGO_ALFABETO = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def generar_codigo_reserva(largo=8):
    # Devuelve un codigo publico que todavia no use ninguna reserva.
    while True:
        codigo = "".join(secrets.choice(CODIGO_ALFABETO) for _ in range(largo))

        if not Reserva.objects.filter(codigo=codigo).exists():
            return codigo


# Reserva: una pista reservada por un cliente en una fecha y horario.
# Guarda el precio de ese momento en precio_hora para que no cambie despues
# si el centro sube los precios (el precio queda congelado en la reserva).
class Reserva(models.Model):
    id_reserva = models.AutoField(primary_key=True)
    # Codigo publico de la reserva: se lo damos al cliente para que despues
    # pueda consultarla o cancelarla sin tener usuario en el sistema.
    codigo = models.CharField(max_length=8, unique=True, editable=False)
    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.PROTECT,
        related_name="reservas"
    )
    pista = models.ForeignKey(
        Pista,
        on_delete=models.PROTECT,
        related_name="reservas"
    )
    fecha = models.DateField()
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    estado = models.ForeignKey(
        EstadoReserva,
        on_delete=models.PROTECT,
        related_name="reservas"
    )
    cantidad_jugadores = models.PositiveIntegerField(
        validators=[MinValueValidator(1)]
    )
    precio_hora = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        editable=False
    )

    def clean(self):
        super().clean()

        errores = {}

        if self.hora_inicio and self.hora_fin:
            if self.hora_fin <= self.hora_inicio:
                errores["hora_fin"] = (
                    "La hora de fin debe ser posterior a la hora de inicio."
                )
            elif self.pista_id:
                duracion_minutos = self.calcularDuracion()
                duracion_minima_minutos = self.pista.obtenerDuracionMinima() * 60

                if duracion_minutos < duracion_minima_minutos:
                    errores["hora_fin"] = (
                        "La reserva no cumple la duración mínima de la pista."
                    )

        if self.pista_id and self.cantidad_jugadores:
            if self.cantidad_jugadores > self.pista.obtenerCapacidadMaxima():
                errores["cantidad_jugadores"] = (
                    "La cantidad de jugadores supera la capacidad de la pista."
                )

        # La reserva tiene que caer dentro de alguna franja de atencion
        # del dia de la semana que corresponde a la fecha reservada.
        if self.fecha and self.hora_inicio and self.hora_fin:
            franjas = HorarioAtencion.objects.filter(
                dia_semana=self.fecha.weekday()
            )

            if not franjas.exists():
                errores["fecha"] = "El centro no abre ese dia."
            else:
                dentro_de_horario = False

                for franja in franjas:
                    if (
                        self.hora_inicio >= franja.hora_apertura
                        and self.hora_fin <= franja.hora_cierre
                    ):
                        dentro_de_horario = True

                if not dentro_de_horario:
                    errores["hora_inicio"] = (
                        "La reserva tiene que estar dentro del horario de atencion."
                    )

        if (
            self.pista_id
            and self.fecha
            and self.hora_inicio
            and self.hora_fin
            and self.hora_fin > self.hora_inicio
        ):
            # solo las reservas que realmente ocupan la pista:
            # una reserva cancelada no bloquea el horario
            reservas = Reserva.objects.filter(
                pista_id=self.pista_id,
                fecha=self.fecha,
                hora_inicio__lt=self.hora_fin,
                hora_fin__gt=self.hora_inicio,
            ).exclude(estado__nombre="cancelada")

            if self.pk:
                reservas = reservas.exclude(pk=self.pk)

            if reservas.exists():
                errores["pista"] = (
                    "La pista ya tiene una reserva en ese horario."
                )

        if errores:
            raise ValidationError(errores)

    def sePuedePedir(self):
        # Una reserva cancelada ya no admite pedidos de cafeteria.
        return self.estado_id and self.estado.nombre != "cancelada"

    def sePuedeCancelar(self):
        # Solo se cancela una reserva pendiente de pago que todavia no empezo.
        if self.estado_id and self.estado.nombre != "pendiente_a_pago":
            return False

        comienzo = timezone.make_aware(
            datetime.combine(self.fecha, self.hora_inicio)
        )

        return comienzo > timezone.now()

    def calcularDuracion(self):
        inicio = (
            self.hora_inicio.hour * 60
            + self.hora_inicio.minute
            + self.hora_inicio.second / 60
        )
        fin = (
            self.hora_fin.hour * 60
            + self.hora_fin.minute
            + self.hora_fin.second / 60
        )

        return fin - inicio

    def calcularCostoPista(self):
        horas = Decimal(str(self.calcularDuracion())) / Decimal("60")
        return horas * self.precio_hora

    def calcularCostoPedidos(self):
        total = Decimal("0")

        for pedido in self.pedidos.all():
            total += pedido.calcularTotal()

        return total

    def calcularCostoTotal(self):
        # costo de la pista + todo lo pedido en la cafeteria
        return self.calcularCostoPista() + self.calcularCostoPedidos()

    def save(self, *args, **kwargs):
        # _state.adding vale True solo cuando la reserva es nueva (todavia
        # no esta guardada en la base). Asi el precio de la pista se copia
        # una sola vez, al crear la reserva, y no se pisa al editarla.
        if self.pista_id and self._state.adding:
            self.precio_hora = self.pista.obtenerPrecioHora()

        # El codigo se genera una sola vez, cuando la reserva es nueva.
        if not self.codigo:
            self.codigo = generar_codigo_reserva()

        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Reserva {self.id_reserva}"

# Partida: una partida jugada dentro de una reserva. Una reserva puede tener varias.
class Partida(models.Model):
    id_partida = models.AutoField(primary_key=True)
    reserva = models.ForeignKey(
        Reserva,
        on_delete=models.PROTECT,
        related_name="partidas"
    )
    numero = models.PositiveIntegerField(
        validators=[MinValueValidator(1)]
    )
    fecha_hora_inicio = models.DateTimeField()
    estado = models.ForeignKey(
        EstadoPartida,
        on_delete=models.PROTECT,
        related_name="partidas"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["reserva", "numero"],
                name="partida_numero_unico_por_reserva"
            )
        ]

    def agregarJugador(self, jugador):
        if Participacion.objects.filter(
            partida=self, jugador=jugador
        ).exists():
            raise ValidationError("El jugador ya participa en esta partida.")

        # la pista de la reserva define cuantos jugadores entran
        if (
            self.reserva.pista.obtenerCapacidadMaxima()
            <= self.participaciones.count()
        ):
            raise ValidationError(
                "Se alcanzo la capacidad maxima de la pista."
            )

        return Participacion.objects.create(
            partida=self,
            jugador=jugador
        )

    def obtenerGanador(self):
        participaciones = self.participaciones.all()

        if not participaciones.exists():
            return None

        ganador = None
        puntaje_maximo = -1

        for participacion in participaciones:
            puntaje = participacion.calcularPuntajeTotal()

            if puntaje > puntaje_maximo:
                ganador = participacion.jugador
                puntaje_maximo = puntaje

        return ganador

    def __str__(self):
        return f"Partida {self.numero} - Reserva {self.reserva_id}"

# Participacion: une un jugador con una partida. Desde aca se calcula el puntaje.
class Participacion(models.Model):
    id_participacion = models.AutoField(primary_key=True)
    partida = models.ForeignKey(
        Partida,
        on_delete=models.CASCADE,
        related_name="participaciones"
    )
    jugador = models.ForeignKey(
        Jugador,
        on_delete=models.PROTECT,
        related_name="participaciones"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["partida", "jugador"],
                name="jugador_unico_por_partida"
            )
        ]

    def siguienteTiro(self):
        # Devuelve (numero_frame, numero_lanzamiento) del proximo tiro del
        # jugador, o None si ya termino sus 10 frames.
        tiros = {}

        for lanz in self.lanzamientos.all():
            tiros.setdefault(lanz.numero_frame, {})[
                lanz.numero_lanzamiento
            ] = lanz.pinos_derribados

        for frame in range(1, 10):
            del_frame = tiros.get(frame, {})

            if 1 not in del_frame:
                return (frame, 1)

            # Con un strike el frame se termina con un solo tiro.
            if del_frame[1] == 10:
                continue

            if 2 not in del_frame:
                return (frame, 2)

        decimo = tiros.get(10, {})

        if 1 not in decimo:
            return (10, 1)

        if 2 not in decimo:
            return (10, 2)

        # En el frame 10 hay tercer tiro solo si hubo strike o spare.
        hubo_bonus = decimo[1] == 10 or decimo[1] + decimo[2] == 10

        if hubo_bonus and 3 not in decimo:
            return (10, 3)

        return None

    def marcasPorFrame(self):
        # Devuelve 10 textos para mostrar: 'X', '9 /', '8 1', etc.
        tiros = {}

        for lanz in self.lanzamientos.order_by(
            "numero_frame", "numero_lanzamiento"
        ):
            tiros.setdefault(lanz.numero_frame, []).append(
                lanz.pinos_derribados
            )

        marcas = []

        for frame in range(1, 11):
            del_frame = tiros.get(frame, [])

            if not del_frame:
                marcas.append("")
            elif frame < 10 and del_frame[0] == 10:
                marcas.append("X")
            elif (
                frame < 10
                and len(del_frame) == 2
                and sum(del_frame) == 10
            ):
                marcas.append(f"{del_frame[0]} /")
            elif frame == 10:
                marcas.append(
                    " · ".join(
                        "X" if tiro == 10 else str(tiro) for tiro in del_frame
                    )
                )
            else:
                marcas.append(" · ".join(str(tiro) for tiro in del_frame))

        return marcas

    def calcularPuntajeTotal(self):
        # 1) Traer todos los lanzamientos de este jugador, ordenados por frame
        lanzamientos = self.lanzamientos.order_by("numero_frame", "numero_lanzamiento")

        # 2) Armar una lista simple con los pinos de cada lanzamiento
        tiros = []
        for lanz in lanzamientos:
            tiros.append(lanz.pinos_derribados)

        # 3) Recorrer la partida frame por frame (son 10 frames)
        puntaje_total = 0
        posicion = 0  # en qué tiro de la lista vamos

        for numero_frame in range(10):
            if posicion >= len(tiros):
                break  # si ya no hay mas tiros, terminamos

            primer_tiro = tiros[posicion]

            # CASO STRIKE: 10 pinos en el primer tiro del frame
            if primer_tiro == 10:
                # Para valer, el strike necesita los 2 tiros siguientes.
                # Si la partida esta en curso y todavia no los hay, se corta.
                if posicion + 2 >= len(tiros):
                    break

                puntaje_total += 10 + tiros[posicion + 1] + tiros[posicion + 2]
                posicion += 1  # el strike ocupa un solo tiro del frame
                continue

            # Sin segundo tiro el frame esta a medio jugar: no se suma nada.
            if posicion + 1 >= len(tiros):
                break

            segundo_tiro = tiros[posicion + 1]

            # CASO SPARE: 10 pinos sumando los 2 tiros del frame
            if primer_tiro + segundo_tiro == 10:
                # El spare vale 10 + el proximo tiro; sin ese tiro no vale.
                if posicion + 2 >= len(tiros):
                    break

                puntaje_total += 10 + tiros[posicion + 2]
                posicion += 2  # el spare ocupa los 2 tiros del frame
                continue

            # CASO FRAME COMUN: se suman los pinos de los 2 tiros
            puntaje_total += primer_tiro + segundo_tiro
            posicion += 2

        return puntaje_total

    def __str__(self):
        return f"{self.jugador} - {self.partida}"

# Lanzamiento: cada tiro del jugador, con su frame, su numero de tiro y los pinos que tumbo.
class Lanzamiento(models.Model):
    id_lanzamiento = models.AutoField(primary_key=True)
    participacion = models.ForeignKey(
        Participacion,
        on_delete=models.CASCADE,
        related_name="lanzamientos"
    )
    participacion_id: int | None
    numero_frame = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10)]
    )
    numero_lanzamiento = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(3)]
    )
    pinos_derribados = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(10)]
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "participacion",
                    "numero_frame",
                    "numero_lanzamiento"
                ],
                name="lanzamiento_unico_por_frame"
            )
        ]

    def clean(self):
        super().clean()

        if self.numero_frame is None or self.numero_lanzamiento is None:
            return

        errores = {}

        if self.numero_frame < 10 and self.numero_lanzamiento == 3:
            errores["numero_lanzamiento"] = (
                "El tercer lanzamiento solo se permite en el frame 10."
            )

        if (
            self.numero_lanzamiento == 2
            and self.participacion_id
            and self.pinos_derribados is not None
        ):
            primero = Lanzamiento.objects.filter(
                participacion_id=self.participacion_id,
                numero_frame=self.numero_frame,
                numero_lanzamiento=1
            )

            if self.pk:
                primero = primero.exclude(pk=self.pk)

            lanzamiento_anterior = primero.first()

            if lanzamiento_anterior:
                if self.numero_frame < 10:
                    if (
                        lanzamiento_anterior.pinos_derribados
                        + self.pinos_derribados > 10
                    ):
                        errores["pinos_derribados"] = (
                            "En los primeros nueve frames no se pueden "
                            "derribar más de 10 pinos en dos lanzamientos."
                        )

        if errores:
            raise ValidationError(errores)

    def save(self, *args, **kwargs):
        # Se valida siempre, tambien cuando el lanzamiento se crea por
        # codigo y no desde el admin o un formulario.
        self.full_clean()
        super().save(*args, **kwargs)

    def esStrike(self):
        # Para ser strike hay que derribar los 10 pinos
        if self.pinos_derribados != 10:
            return False

        # En los frames 1 al 9, solo el primer lanzamiento puede ser strike
        if self.numero_frame < 10:
            return self.numero_lanzamiento == 1

        # En el frame 10 la pista se resetea con cada strike o spare,
        # asi que el 2do y el 3er lanzamiento tambien pueden ser strike
        return True

    def esSpare(self):
        # El spare es siempre el segundo lanzamiento del frame
        if self.numero_lanzamiento != 2:
            return False

        if self.participacion_id is None:
            return False

        # Buscamos el primer lanzamiento de este mismo frame
        primero = Lanzamiento.objects.filter(
            participacion_id=self.participacion_id,
            numero_frame=self.numero_frame,
            numero_lanzamiento=1
        ).first()

        if primero is None:
            return False

        # Es spare si ambos lanzamientos suman 10 y el primero no fue strike
        return (
            primero.pinos_derribados < 10
            and primero.pinos_derribados + self.pinos_derribados == 10
        )

    def __str__(self):
        return (
            f"Frame {self.numero_frame}, "
            f"lanzamiento {self.numero_lanzamiento}"
        )

# Producto: lo que se vende en la confiteria, comida o bebida.
class Producto(models.Model):
    COMIDA = "comida"
    BEBIDA = "bebida"

    TIPOS = [
        (COMIDA, "Comida"),
        (BEBIDA, "Bebida"),
    ]

    id_producto = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    precio = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))]
    )
    tipo = models.CharField(max_length=10, choices=TIPOS)

    def clean(self):
        super().clean()
        self.validarPrecio()

    def validarPrecio(self):
        if self.precio is not None and self.precio <= 0:
            raise ValidationError({"precio": "El precio debe ser positivo."})

    def __str__(self):
        return self.nombre

# Pedido: el pedido de productos que se hace dentro de una reserva.
class Pedido(models.Model):
    id_pedido = models.AutoField(primary_key=True)
    reserva = models.ForeignKey(
        Reserva,
        on_delete=models.PROTECT,
        related_name="pedidos"
    )
    fecha_hora_pedido = models.DateTimeField(auto_now_add=True)
    estado = models.ForeignKey(
        EstadoPedido,
        on_delete=models.PROTECT,
        related_name="pedidos"
    )

    @transaction.atomic
    def agregarDetalle(self, producto, cantidad):
        # @transaction.atomic: todo lo de abajo es una sola operacion.
        # Si algo falla (por ejemplo el detalle), Django deshace los
        # cambios y el pedido NO queda guardado a medias.
        if cantidad < 1:
            raise ValidationError("La cantidad debe ser como mínimo 1.")

        if not self.pk:
            self.save()

        detalle = DetallePedido(
            pedido=self,
            producto=producto,
            cantidad=cantidad,
            precio_unitario=producto.precio
        )

        detalle.full_clean()
        detalle.save()

        return detalle

    def calcularTotal(self):
        total = Decimal("0.00")

        for detalle in self.detalles.all():
            total += detalle.calcularSubtotal()

        return total

    def cerrar(self):
        self.estado = EstadoPedido.objects.get(nombre="cerrado")
        self.full_clean()
        self.save()

    def __str__(self):
        return f"Pedido {self.id_pedido}"


# DetallePedido: cada producto dentro de un pedido, con la cantidad y el precio
# del momento de la compra (ese precio tampoco se toca despues).
class DetallePedido(models.Model):
    id_detalle = models.AutoField(primary_key=True)
    pedido = models.ForeignKey(
        Pedido,
        on_delete=models.CASCADE,
        related_name="detalles"
    )
    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        related_name="detalles"
    )
    cantidad = models.PositiveIntegerField(
        validators=[MinValueValidator(1)]
    )
    precio_unitario = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))]
    )

    def clean(self):
        super().clean()
        self.validarCantidad()

    def calcularSubtotal(self):
        return self.precio_unitario * self.cantidad

    def validarCantidad(self):
        if self.cantidad is not None and self.cantidad < 1:
            raise ValidationError({"cantidad": "La cantidad debe ser como mínimo 1."})

    def __str__(self):
        return f"{self.producto} x {self.cantidad}"

# HorarioAtencion: los dias y horarios en que el centro abre.
# Se usa para no dejar reservar un dia cerrado o fuera del horario de atencion.
class HorarioAtencion(models.Model):
    LUNES = 0
    MARTES = 1
    MIERCOLES = 2
    JUEVES = 3
    VIERNES = 4
    SABADO = 5
    DOMINGO = 6

    DIAS = [
        (LUNES, "Lunes"),
        (MARTES, "Martes"),
        (MIERCOLES, "Miercoles"),
        (JUEVES, "Jueves"),
        (VIERNES, "Viernes"),
        (SABADO, "Sabado"),
        (DOMINGO, "Domingo"),
    ]

    id_horario = models.AutoField(primary_key=True)
    dia_semana = models.PositiveSmallIntegerField(choices=DIAS)
    hora_apertura = models.TimeField()
    hora_cierre = models.TimeField()

    class Meta:
        ordering = ["dia_semana", "hora_apertura"]
        constraints = [
            models.UniqueConstraint(
                fields=["dia_semana", "hora_apertura"],
                name="horario_unico_por_dia"
            )
        ]

    def clean(self):
        super().clean()

        if (
            self.hora_apertura
            and self.hora_cierre
            and self.hora_cierre <= self.hora_apertura
        ):
            raise ValidationError({
                "hora_cierre": "La hora de cierre debe ser posterior a la de apertura."
            })

    def __str__(self):
        return (
            f"{self.get_dia_semana_display()} "
            f"{self.hora_apertura:%H:%M} a {self.hora_cierre:%H:%M}"
        )
