from django.db import models
from django.core.validators import RegexValidator

# Validador para DNI (8 dígitos)
dni_validator = RegexValidator(
    regex=r'^\d{8}$',
    message="El DNI debe tener 8 dígitos."
)

class Cobrador(models.Model):
    nombre = models.CharField(max_length=200, verbose_name="Nombre", blank=False, null=False)
    dni = models.CharField(
        max_length=8,
        unique=True,
        validators=[dni_validator],
        verbose_name="DNI"
    )
    telefono = models.CharField(max_length=15, blank=True, null=True, verbose_name="Teléfono")
    correo = models.EmailField(blank=True, null=True, verbose_name="Correo")
    direccion = models.TextField(blank=True, null=True, verbose_name="Dirección")
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Cobrador"
        verbose_name_plural = "Cobradores"
        ordering = ['nombre']

    def __str__(self):
        return f"{self.nombre} ({self.dni})"