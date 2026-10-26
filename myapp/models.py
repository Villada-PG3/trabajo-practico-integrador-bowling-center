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

    def clear(self):
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

    