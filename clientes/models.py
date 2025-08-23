from django.db import models
from django.core.validators import RegexValidator

from django.contrib.auth.models import User
from cobradores.models import Cobrador

# Validador para DNI (8 dígitos) o RUC (11 dígitos)
ruc_dni_validator = RegexValidator(
    regex=r'^\d{8,11}$',
    message="El DNI debe tener 8 dígitos o el RUC 11 dígitos."
)

class Cliente(models.Model):
    nombre = models.CharField(max_length=200, verbose_name="Nombre", blank=False, null=False)
    dni_ruc = models.CharField(
        max_length=11,
        unique=True,
        validators=[ruc_dni_validator],
        verbose_name="DNI/RUC"
    )
    direccion = models.TextField(blank=True, null=True, verbose_name="Dirección")
    telefono = models.CharField(max_length=15, blank=True, null=True, verbose_name="Teléfono")
    correo = models.EmailField(blank=True, null=True, verbose_name="Correo")
    notas = models.TextField(blank=True, null=True, verbose_name="Notas")
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        ordering = ['nombre']

    def __str__(self):
        return f"{self.nombre} ({self.dni_ruc})"
    


class LogActividad(models.Model):
    CATEGORIA_OPCIONES = [
        ('cliente', 'Cliente'),
        ('documento', 'Documento'),
        ('cobro', 'Cobro'),
        ('devolucion', 'Devolución'),
        ('reporte', 'Reporte'),
        ('otro', 'Otro'),
    ]

    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    cobrador = models.ForeignKey(Cobrador, on_delete=models.SET_NULL, null=True, blank=True)
    categoria = models.CharField(max_length=20, choices=CATEGORIA_OPCIONES)
    accion = models.CharField(max_length=255)
    descripcion = models.TextField(blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha']

    def __str__(self):
        quien = self.cobrador or self.usuario or "Sistema"
        return f"{quien} - {self.accion}"
    



class EmpresaConfig(models.Model):
    nombre = models.CharField(max_length=100, default="Mi Empresa")
    ruc = models.CharField(max_length=11, blank=True, null=True)
    direccion = models.CharField(max_length=200, blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    correo = models.EmailField(blank=True, null=True)
    logo = models.ImageField(upload_to='logos/', blank=True, null=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.nombre