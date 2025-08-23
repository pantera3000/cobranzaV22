from django import forms
from .models import Documento
from clientes.models import Cliente
from cobradores.models import Cobrador
import datetime
from django.utils import timezone

def localtime_peru():
    return timezone.localtime(timezone.now())

class DocumentoForm(forms.ModelForm):
    # ✅ Campo de búsqueda (visible para el usuario)
    cliente_busqueda = forms.CharField(
        label='Cliente',
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Buscar cliente por nombre o DNI/RUC...',
            'autocomplete': 'off'
        })
    )

    class Meta:
        model = Documento
        fields = [
            'cliente', 'cobrador', 'tipo', 'serie', 'numero',
            'fecha_emision', 'fecha_vencimiento',
            'monto_total'
        ]
        widgets = {
            'cliente': forms.HiddenInput(),  # ✅ Ahora oculto
            'cobrador': forms.Select(attrs={'class': 'form-control'}),
            'tipo': forms.Select(attrs={'class': 'form-control'}),
            'serie': forms.TextInput(attrs={'class': 'form-control'}),
            'numero': forms.TextInput(attrs={'class': 'form-control'}),
            'fecha_emision': forms.DateTimeInput(
                attrs={'type': 'datetime-local', 'class': 'form-control'},
                format='%Y-%m-%dT%H:%M'
            ),
            'fecha_vencimiento': forms.DateTimeInput(
                attrs={'type': 'datetime-local', 'class': 'form-control'},
                format='%Y-%m-%dT%H:%M'
            ),
            'monto_total': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }
        labels = {
            'cliente': 'Cliente',
            'cobrador': 'Cobrador',
            'tipo': 'Tipo de Documento',
            'serie': 'Serie',
            'numero': 'Número',
            'fecha_emision': 'Fecha de Emisión',
            'fecha_vencimiento': 'Fecha de Vencimiento',
            'monto_total': 'Monto Total (S/)',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Preseleccionar fecha actual en hora de Perú
        now_peru = localtime_peru()
        if not self.instance.pk:  # Solo en creación
            self.fields['fecha_emision'].initial = now_peru.strftime('%Y-%m-%dT%H:%M')
            # Por defecto: vencimiento en 30 días
            vencimiento = now_peru + datetime.timedelta(days=30)
            self.fields['fecha_vencimiento'].initial = vencimiento.strftime('%Y-%m-%dT%H:%M')

        # ✅ Manejo de cliente: si viene en GET o initial, preseleccionar
        cliente_id = self.data.get('cliente') or self.initial.get('cliente')
        if cliente_id:
            try:
                cliente = Cliente.objects.get(pk=cliente_id)
                # ✅ Preseleccionar cliente en el campo oculto
                self.fields['cliente'].initial = cliente
                # ✅ Rellenar campo de búsqueda
                self.fields['cliente_busqueda'].initial = f"{cliente.nombre} ({cliente.dni_ruc})"
            except Cliente.DoesNotExist:
                pass

        # ✅ Limitar queryset de cliente a solo el seleccionado (opcional)
        if self.fields['cliente'].initial:
            self.fields['cliente'].queryset = Cliente.objects.filter(pk=self.fields['cliente'].initial.pk)
        else:
            self.fields['cliente'].queryset = Cliente.objects.all().order_by('nombre')

        # Cobradores
        self.fields['cobrador'].queryset = Cobrador.objects.all().order_by('nombre')