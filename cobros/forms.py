from django import forms
from .models import Cobro
from cobradores.models import Cobrador
from documentos.models import Documento
import datetime
from django.utils import timezone
from django.db import models  # ✅ ¡Este es el que falta!

def localtime_peru():
    return timezone.localtime(timezone.now())

class CobroForm(forms.ModelForm):
    class Meta:
        model = Cobro
        fields = ['documento', 'cobrador', 'monto', 'fecha', 'referencia', 'notas']  # ✅ Añadidos: referencia y notas
        widgets = {
            'documento': forms.HiddenInput(),  # ✅ Mantenido
            'cobrador': forms.Select(attrs={'class': 'form-control'}),
            'monto': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
            'fecha': forms.DateTimeInput(
                attrs={'type': 'datetime-local', 'class': 'form-control'},
                format='%Y-%m-%dT%H:%M'
            ),
            'referencia': forms.TextInput(attrs={  # ✅ Campo existente
                'class': 'form-control',
                'placeholder': 'Ej: REC-001, Depósito, Transferencia'
            }),
            'notas': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Notas (opcional)...',
                'maxlength': '60',
                'oninput': "this.nextElementSibling.textContent = this.value.length + '/60'"
            }),
        }
        labels = {
            'documento': 'Documento a pagar',
            'cobrador': 'Cobrador',
            'monto': 'Monto Pagado (S/)',
            'fecha': 'Fecha del Pago',
            'referencia': 'Referencia / N° Operación',
            'notas': 'Notas Adicionales',
        }
        help_texts = {
            'referencia': 'Número de recibo, transferencia, depósito, etc.',
            'notas': 'Máximo 60 caracteres. Visible en listas y tarjetas.',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Calcular saldo pendiente
        saldo_pendiente = models.ExpressionWrapper(
            models.F('monto_total') - models.F('monto_pagado') - models.F('monto_devolucion'),
            output_field=models.DecimalField()
        )
        documentos_pendientes = Documento.objects.annotate(saldo=saldo_pendiente).filter(saldo__gt=0).select_related('cliente')

        # ✅ Si hay documento en initial, ajustar queryset
        if 'documento' in self.initial and self.initial['documento']:
            doc = self.initial['documento']
            self.fields['documento'].queryset = Documento.objects.filter(pk=doc.pk)
        else:
            self.fields['documento'].queryset = documentos_pendientes

        self.fields['cobrador'].queryset = Cobrador.objects.all().order_by('nombre')
        self.fields['fecha'].initial = localtime_peru().strftime('%Y-%m-%dT%H:%M')