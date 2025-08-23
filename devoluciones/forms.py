import json
from django import forms
from .models import Devolucion
from cobradores.models import Cobrador
from documentos.models import Documento
from django.utils import timezone

def localtime_peru():
    return timezone.localtime(timezone.now())

class DevolucionForm(forms.ModelForm):
    class Meta:
        model = Devolucion
        fields = ['documento', 'cobrador', 'monto', 'fecha', 'notas']  # ✅ Añadido
        widgets = {
            'documento': forms.HiddenInput(),  # ✅ Cambiado a HiddenInput
            'cobrador': forms.Select(attrs={'class': 'form-control'}),
            'monto': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
            'fecha': forms.DateTimeInput(
                attrs={'type': 'datetime-local', 'class': 'form-control'},
                format='%Y-%m-%dT%H:%M'
            ),
            'notas': forms.Textarea(attrs={  # ✅ Widget con límite
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Notas (opcional)...',
                'maxlength': '60',
                'oninput': "this.nextElementSibling.textContent = this.value.length + '/60'"
            }),


        }
        labels = {
            'documento': 'Documento al que se devuelve',
            'cobrador': 'Cobrador',
            'monto': 'Monto de Devolución (S/)',
            'fecha': 'Fecha de Devolución',
            'notas': 'Notas Adicionales',
        }
        
        help_texts = {
            'notas': 'Máximo 60 caracteres.',
        }


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Todos los documentos
        self.fields['documento'].queryset = Documento.objects.select_related('cliente').all().order_by('-fecha_emision')

        # Si hay initial['documento'], ajustar queryset
        if 'documento' in self.initial and self.initial['documento']:
            doc = self.initial['documento']
            self.fields['documento'].queryset = Documento.objects.filter(pk=doc.pk)

        self.fields['cobrador'].queryset = Cobrador.objects.all().order_by('nombre')
        self.fields['fecha'].initial = localtime_peru().strftime('%Y-%m-%dT%H:%M')