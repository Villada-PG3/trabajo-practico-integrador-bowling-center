from django import forms
from django.core.exceptions import NON_FIELD_ERRORS
from .models import HorarioAtencion, Pista, Reserva, TipoPista

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


class TipoPistaForm(forms.ModelForm):
    """
    Formulario del panel de gestion para cargar y editar tipos de pista.

    Define el precio por hora, la capacidad y la duracion minima que
    heredan las pistas de ese tipo. El nombre lo elige el centro.
    """

    class Meta:
        model = TipoPista
        fields = [
            "nombre",
            "descripcion",
            "precio_hora",
            "capacidad_maxima",
            "duracion_minima",
        ]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
            "descripcion": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
            "precio_hora": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "min": "0.01"}
            ),
            "capacidad_maxima": forms.NumberInput(
                attrs={"class": "form-control", "min": 1}
            ),
            "duracion_minima": forms.NumberInput(
                attrs={"class": "form-control", "min": 1}
            ),
        }
        labels = {
            "nombre": "Nombre del tipo",
            "descripcion": "Descripción",
            "precio_hora": "Precio por hora ($)",
            "capacidad_maxima": "Capacidad máxima (jugadores)",
            "duracion_minima": "Duración mínima (horas)",
        }
        error_messages = {
            "nombre": {
                "unique": "Ya existe un tipo de pista con este nombre.",
            },
        }


class PistaForm(forms.ModelForm):
    """
    Formulario del panel de gestion para cargar y editar pistas.

    El numero de pista lo asigna la base de datos. El precio propio es
    opcional: si se deja vacio, la pista usa el precio de su tipo.
    """

    class Meta:
        model = Pista
        fields = ["tipo_pista", "precio_hora", "disponible"]
        widgets = {
            "tipo_pista": forms.Select(attrs={"class": "form-select"}),
            "precio_hora": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "min": "0.01"}
            ),
            "disponible": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
        }
        labels = {
            "tipo_pista": "Tipo de pista",
            "precio_hora": "Precio por hora propio ($)",
            "disponible": "¿Disponible para reservar?",
        }
        help_texts = {
            "precio_hora": "Dejalo vacío para usar el precio del tipo de pista.",
        }

    def clean_precio_hora(self):
        precio = self.cleaned_data["precio_hora"]

        if precio is not None and precio <= 0:
            raise forms.ValidationError("El precio debe ser mayor que cero.")

        return precio


class HorarioAtencionForm(forms.ModelForm):
    """
    Formulario del panel de gestion para cargar y editar los horarios de
    atencion. Se pueden cargar varias franjas el mismo dia.

    Que el cierre sea posterior a la apertura lo valida
    HorarioAtencion.clean(), y que no se repita la misma apertura el mismo
    dia lo valida la restriccion unica del modelo. El formulario no repite
    esas reglas.
    """

    class Meta:
        model = HorarioAtencion
        fields = ["dia_semana", "hora_apertura", "hora_cierre"]
        widgets = {
            "dia_semana": forms.Select(attrs={"class": "form-select"}),
            "hora_apertura": forms.TimeInput(
                format="%H:%M",
                attrs={"class": "form-control", "type": "time"},
            ),
            "hora_cierre": forms.TimeInput(
                format="%H:%M",
                attrs={"class": "form-control", "type": "time"},
            ),
        }
        labels = {
            "dia_semana": "Día de la semana",
            "hora_apertura": "Hora de apertura",
            "hora_cierre": "Hora de cierre",
        }
        error_messages = {
            NON_FIELD_ERRORS: {
                "unique_together": (
                    "Ya existe un horario de atención con este día "
                    "y esta hora de apertura."
                ),
            },
        }