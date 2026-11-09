from django.db import migrations


def crear_estado_en_curso(apps, schema_editor):
    EstadoReserva = apps.get_model("myapp", "EstadoReserva")
    EstadoReserva.objects.get_or_create(nombre="en_curso")


def borrar_estado_en_curso(apps, schema_editor):
    EstadoReserva = apps.get_model("myapp", "EstadoReserva")
    Reserva = apps.get_model("myapp", "Reserva")

    if not Reserva.objects.filter(estado__nombre="en_curso").exists():
        EstadoReserva.objects.filter(nombre="en_curso").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("myapp", "0006_estado_partida_pendiente"),
    ]

    operations = [
        migrations.RunPython(crear_estado_en_curso, borrar_estado_en_curso),
    ]
