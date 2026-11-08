import secrets

from django.db import migrations, models

# Mismo alfabeto que en models.py: sin caracteres que se confunden (0/O, 1/I).
CODIGO_ALFABETO = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def generar_codigos(apps, schema_editor):
    """Completa el codigo de las reservas que ya existian."""
    Reserva = apps.get_model("myapp", "Reserva")

    usados = set(Reserva.objects.values_list("codigo", flat=True))

    for reserva in Reserva.objects.filter(codigo__isnull=True):
        while True:
            codigo = "".join(secrets.choice(CODIGO_ALFABETO) for _ in range(8))
            if codigo not in usados:
                break

        usados.add(codigo)
        reserva.codigo = codigo
        reserva.save(update_fields=["codigo"])


class Migration(migrations.Migration):

    dependencies = [
        ("myapp", "0004_pista_disponible_pista_precio_hora_horarioatencion"),
    ]

    operations = [
        # 1) Se agrega el campo permitiendo vacio, para las reservas viejas.
        migrations.AddField(
            model_name="reserva",
            name="codigo",
            field=models.CharField(max_length=8, null=True),
        ),
        # 2) Se completa el codigo de las reservas que ya estaban cargadas.
        migrations.RunPython(generar_codigos, migrations.RunPython.noop),
        # 3) Ahora si, obligatorio y unico.
        migrations.AlterField(
            model_name="reserva",
            name="codigo",
            field=models.CharField(editable=False, max_length=8, unique=True),
        ),
    ]
