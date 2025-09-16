from django.db import models
from django.core.validators import RegexValidator
from django.contrib.auth.models import User  # ✅ Importar User

# Validador para DNI (8 dígitos)
dni_validator = RegexValidator(
    regex=r'^\d{8}$',
    message="El DNI debe tener 8 dígitos."
)

class Cobrador(models.Model):
    nombre = models.CharField(max_length=200, verbose_name="Nombre", blank=False, null=False)
    activo = models.BooleanField(default=True)
    dni = models.CharField(
        max_length=8,
        unique=True,
        validators=[dni_validator],
        verbose_name="DNI"
    )
    telefono = models.CharField(max_length=15, blank=True, null=True, verbose_name="Teléfono")
    correo = models.EmailField(blank=True, null=True, verbose_name="Correo")
    direccion = models.TextField(blank=True, null=True, verbose_name="Dirección")
    
    # ✅ Nuevo campo: usuario asociado (opcional por ahora)
    user = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cobrador',  # Permite: user.cobrador
        help_text="Usuario del sistema asociado a este cobrador (opcional)"
    )

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Cobrador"
        verbose_name_plural = "Cobradores"
        ordering = ['nombre']

    def __str__(self):
        if self.user:
            return f"{self.nombre} ({self.dni}) - {self.user.username}"
        return f"{self.nombre} ({self.dni})"