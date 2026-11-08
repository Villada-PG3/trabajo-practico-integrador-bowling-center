from django import forms

from .models import Pista, Reserva


class ReservaForm(forms.ModelForm):
    """
    Formulario de reserva del sitio publico.

    Los campos pista, fecha, hora_inicio, hora_fin y cantidad_jugadores son
    del modelo Reserva. Los datos del titular (nombre, direccion, telefono y
    email) no existen en Reserva: son campos extra que la vista usa para
    crear el Cliente y asociarlo a la reserva.

    El formulario NO repite las reglas de negocio (horario de atencion,
    duracion minima, capacidad y superposicion): eso ya lo valida
    Reserva.clean(), que se ejecuta en Reserva.save().
    """

    nombre = forms.CharField(
        max_length=100,
        label="Nombre y apellido",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    direccion = forms.CharField(
        max_length=200,
        label="Direccion",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    telefono = forms.CharField(
        max_length=30,
        label="Telefono",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    email = forms.EmailField(
        max_length=100,
        label="Email",
        widget=forms.EmailInput(attrs={"class": "form-control"}),
    )

    class Meta:
        model = Reserva
        fields = ["pista", "fecha", "hora_inicio", "hora_fin", "cantidad_jugadores"]
        widgets = {
            "pista": forms.Select(attrs={"class": "form-select"}),
            # La fecha la elige el cliente en el calendario del template y
            # la hora de fin se calcula con la duracion elegida. Por eso los
            # dos viajan en campos ocultos.
            "fecha": forms.DateInput(
                format="%Y-%m-%d", attrs={"type": "hidden"}
            ),
            "hora_fin": forms.TimeInput(
                format="%H:%M", attrs={"type": "hidden"}
            ),
            "hora_inicio": forms.TimeInput(
                format="%H:%M",
                attrs={"class": "form-control", "type": "time"},
            ),

            "cantidad_jugadores": forms.NumberInput(
                attrs={"class": "form-control", "min": 1}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Solo se pueden reservar pistas marcadas como disponibles.
        self.fields["pista"].queryset = Pista.objects.filter(
            disponible=True
        ).select_related("tipo_pista")
        self.fields["pista"].empty_label = "Elegi una pista"
        # Arranca en 4 jugadores, que es lo mas comun; se puede cambiar.
        if not self.is_bound:
            self.fields["cantidad_jugadores"].initial = 4
        # En el desplegable se muestra el tipo y la tarifa de cada pista.
        self.fields["pista"].label_from_instance = (
            lambda pista: (
                f"Pista {pista.numero_pista} - {pista.tipo_pista.nombre} "
                f"(${pista.obtenerPrecioHora()}/h)"
            )
        )


class BuscarReservaForm(forms.Form):
    """El cliente escribe el codigo que le dimos al reservar."""

    codigo = forms.CharField(
        max_length=8,
        label="Codigo de reserva",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Ej: 7KQ2M9XA",
                "autocomplete": "off",
            }
        ),
    )

    def clean_codigo(self):
        codigo = self.cleaned_data["codigo"].strip().upper()

        if not Reserva.objects.filter(codigo=codigo).exists():
            raise forms.ValidationError(
                "No encontramos ninguna reserva con ese codigo."
            )

        return codigo
