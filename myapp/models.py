from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models import Q

# Modelos de Tipo y Estado
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

    def clean(self):
        super().clean()

        if self.nombre and self.nombre not in ["SMALL", "MEDIUM", "LARGE"]:
            raise ValidationError({
                "nombre": "El nombre debe ser SMALL, MEDIUM o LARGE."
            })

    def validarPrecioHora(self):
        if self.precio_hora <= 0:
            raise ValidationError("El precio por hora debe ser positivo.")

    def validarCapacidad(self):
        if self.capacidad_maxima < 1:
            raise ValidationError("La capacidad debe ser como mínimo 1.")

    def __str__(self):
        return self.nombre

class EstadoReserva(models.Model):
    id_estado_reserva = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=50, unique=True)
    descripcion = models.TextField(blank=True)

    def __str__(self):
        return self.nombre

class EstadoPedido(models.Model):
    id_estado_pedido = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.nombre

class EstadoPartida(models.Model):
    id_estado_partida = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.nombre

class Cliente(models.Model):
    id_cliente = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    direccion = models.CharField(max_length=200)
    telefono = models.CharField(max_length=30)
    email = models.CharField(max_length=100)

    def asignarDatos(self, nombre, direccion, telefono, email):
        self.nombre = nombre
        self.direccion = direccion
        self.telefono = telefono
        self.email = email

    def validarEmail(self):
        from django.core.validators import validate_email

        validate_email(self.email)

    def __str__(self):
        return self.nombre

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

class Pista(models.Model):
    numero_pista = models.AutoField(primary_key=True)
    tipo_pista = models.ForeignKey(
        TipoPista,
        on_delete=models.PROTECT,
        related_name="pistas"
    )

    def obtenerCapacidadMaxima(self):
        return self.tipo_pista.capacidad_maxima

    def obtenerPrecioHora(self):
        return self.tipo_pista.precio_hora

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

class Reserva(models.Model):
    id_reserva = models.AutoField(primary_key=True)
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

        if (
            self.pista_id
            and self.fecha
            and self.hora_inicio
            and self.hora_fin
            and self.hora_fin > self.hora_inicio
        ):
            reservas = Reserva.objects.filter(
                pista_id=self.pista_id,
                fecha=self.fecha,
                hora_inicio__lt=self.hora_fin,
                hora_fin__gt=self.hora_inicio
            )

            if self.pk:
                reservas = reservas.exclude(pk=self.pk)

            if reservas.exists():
                errores["pista"] = (
                    "La pista ya tiene una reserva en ese horario."
                )

        if errores:
            raise ValidationError(errores)

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

    def calcularCostoTotal(self):
        total = self.calcularCostoPista()

        for pedido in self.pedidos.all():
            total += pedido.calcularTotal()

        return total

    def validarDisponibilidad(self):
        if not self.pista.estaDisponible(
            self.fecha, self.hora_inicio, self.hora_fin
        ):
            raise ValidationError("La pista no está disponible.")

    def validarCapacidad(self):
        if self.cantidad_jugadores > self.pista.obtenerCapacidadMaxima():
            raise ValidationError("Se supera la capacidad de la pista.")

    def save(self, *args, **kwargs):
        if self.pista_id and not self.pk:
            self.precio_hora = self.pista.obtenerPrecioHora()

        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Reserva {self.id_reserva}"

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
                # el strike vale 10 + los 2 tiros siguientes
                tiro_siguiente = 0
                if posicion + 1 < len(tiros):
                    tiro_siguiente = tiros[posicion + 1]

                tiro_posterior = 0
                if posicion + 2 < len(tiros):
                    tiro_posterior = tiros[posicion + 2]

                puntaje_total += 10 + tiro_siguiente + tiro_posterior
                posicion += 1  # el strike ocupa un solo tiro del frame

            # CASO SPARE: 10 pinos sumando los 2 tiros del frame
            elif primer_tiro + tiros[posicion + 1] == 10:
                # el spare vale 10 + el proximo tiro
                tiro_siguiente = 0
                if posicion + 2 < len(tiros):
                    tiro_siguiente = tiros[posicion + 2]

                puntaje_total += 10 + tiro_siguiente
                posicion += 2  # el spare ocupa los 2 tiros del frame

            # CASO FRAME COMUN: se suman los pinos de los 2 tiros
            else:
                segundo_tiro = tiros[posicion + 1]
                puntaje_total += primer_tiro + segundo_tiro
                posicion += 2

        return puntaje_total

    def __str__(self):
        return f"{self.jugador} - {self.partida}"

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

    def agregarDetalle(self, producto, cantidad):
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