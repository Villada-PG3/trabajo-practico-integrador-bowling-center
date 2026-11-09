from decimal import Decimal

from django.db import migrations

ESTADOS_RESERVA = ["pendiente_a_pago", "finalizada", "pagada", "cancelada"]
ESTADOS_PEDIDO = ["abierto", "cerrado", "cancelado"]
ESTADOS_PARTIDA = ["en_curso", "finalizada"]

TIPOS_PISTA = [
    ("SMALL", "Pista chica", Decimal("3000.00"), 4, 1),
    ("MEDIUM", "Pista mediana", Decimal("6000.00"), 6, 1),
    ("LARGE", "Pista grande", Decimal("9000.00"), 8, 1),
]


def cargar_datos(apps, schema_editor):
    EstadoReserva = apps.get_model("myapp", "EstadoReserva")
    EstadoPedido = apps.get_model("myapp", "EstadoPedido")
    EstadoPartida = apps.get_model("myapp", "EstadoPartida")
    TipoPista = apps.get_model("myapp", "TipoPista")

    for nombre in ESTADOS_RESERVA:
        EstadoReserva.objects.get_or_create(nombre=nombre)

    for nombre in ESTADOS_PEDIDO:
        EstadoPedido.objects.get_or_create(nombre=nombre)

    for nombre in ESTADOS_PARTIDA:
        EstadoPartida.objects.get_or_create(nombre=nombre)

    for nombre, descripcion, precio, capacidad, duracion in TIPOS_PISTA:
        TipoPista.objects.get_or_create(
            nombre=nombre,
            defaults={
                "descripcion": descripcion,
                "precio_hora": precio,
                "capacidad_maxima": capacidad,
                "duracion_minima": duracion,
            },
        )


def borrar_datos(apps, schema_editor):
    apps.get_model("myapp", "EstadoReserva").objects.filter(
        nombre__in=ESTADOS_RESERVA
    ).delete()
    apps.get_model("myapp", "EstadoPedido").objects.filter(
        nombre__in=ESTADOS_PEDIDO
    ).delete()
    apps.get_model("myapp", "EstadoPartida").objects.filter(
        nombre__in=ESTADOS_PARTIDA
    ).delete()
    apps.get_model("myapp", "TipoPista").objects.filter(
        nombre__in=[t[0] for t in TIPOS_PISTA]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("myapp", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(cargar_datos, borrar_datos),
    ]