from django import forms
from .models import Cobrador

class CobradorForm(forms.ModelForm):
    class Meta:
        model = Cobrador
        fields = ['nombre', 'dni', 'telefono', 'correo', 'direccion']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'dni': forms.TextInput(attrs={'class': 'form-control'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'correo': forms.EmailInput(attrs={'class': 'form-control'}),
            'direccion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        labels = {
            'nombre': 'Nombre',
            'dni': 'DNI',
            'telefono': 'Teléfono',
            'correo': 'Correo',
            'direccion': 'Dirección',
        }