from django.db import migrations


def crear_estado_pendiente(apps, schema_editor):
    """La partida se crea al reservar, antes de que el juego empiece."""
    EstadoPartida = apps.get_model("myapp", "EstadoPartida")
    EstadoPartida.objects.get_or_create(nombre="pendiente")


def borrar_estado_pendiente(apps, schema_editor):
    EstadoPartida = apps.get_model("myapp", "EstadoPartida")
    EstadoPartida.objects.filter(nombre="pendiente").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("myapp", "0005_reserva_codigo"),
    ]

    operations = [
        migrations.RunPython(crear_estado_pendiente, borrar_estado_pendiente),
    ]
