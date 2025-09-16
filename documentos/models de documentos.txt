from django.db import models
from django.urls import reverse
from clientes.models import Cliente
from cobradores.models import Cobrador
from django.core.validators import MinValueValidator
from decimal import Decimal
import datetime
from django.utils import timezone
import pytz 





# Zona horaria de Perú
def localtime_peru():
    return timezone.localtime(timezone.now())


def get_estado_display_badge(self):
    estado = self.get_estado()
    if estado == 'pagado':
        return 'success'
    elif estado == 'vencido':
        return 'danger'
    else:
        return 'warning'


# Tipos de documentos
TIPO_DOCUMENTO_CHOICES = [
    ('factura', 'Factura'),
    ('boleta', 'Boleta'),
    ('nota_pedido', 'Nota de Pedido'),
    ('nota_venta', 'Nota de Venta'),
    ('otro', 'Otro'),
]

class Documento(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, verbose_name="Cliente")
    cobrador = models.ForeignKey(Cobrador, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Cobrador")
    tipo = models.CharField(max_length=20, choices=TIPO_DOCUMENTO_CHOICES, verbose_name="Tipo")
    serie = models.CharField(max_length=20, blank=True, null=True, verbose_name="Serie")
    numero = models.CharField(max_length=20, verbose_name="Número")
    fecha_emision = models.DateTimeField(default=localtime_peru, verbose_name="Fecha de Emisión")
    fecha_vencimiento = models.DateTimeField(verbose_name="Fecha de Vencimiento")
    monto_total = models.DecimalField(
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Monto Total"
    )
    monto_pagado = models.DecimalField(
        max_digits=12, decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Monto Pagado"
    )
    monto_devolucion = models.DecimalField(
        max_digits=12, decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Devolución"
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Documento"
        verbose_name_plural = "Documentos"
        ordering = ['-fecha_emision']

    def __str__(self):
        return f"{self.get_tipo_display()} {self.get_numero_completo()} - {self.cliente.nombre}"

    # --- Métodos del modelo ---
    def get_numero_completo(self):
        """Devuelve Serie-Número o solo Número si no hay serie"""
        if self.serie:
            return f"{self.serie}-{self.numero}"
        return self.numero

    def get_saldo_pendiente(self):
        return self.monto_total - self.monto_pagado - self.monto_devolucion




    def get_estado(self):
        """
        Devuelve el estado del documento:
        - 'pagado': si no hay saldo pendiente
        - 'pago_parcial': si tiene pagos pero aún hay saldo
        - 'vencido': si está vencido y no está pagado (incluye pago parcial vencido)
        - 'pendiente': si no tiene pagos y no está vencido
        """
        saldo = self.get_saldo_pendiente()
        ahora = localtime_peru()

        # Si está completamente pagado
        if saldo <= 0:
            return 'pagado'

        # Si está vencido (independientemente de si tiene pagos o no)
        if self.fecha_vencimiento < ahora:
            return 'vencido'

        # Si tiene pagos pero no está completo
        if self.monto_pagado > 0 and saldo > 0:
            return 'pago_parcial'

        # Si no tiene pagos y no está vencido
        return 'pendiente'

    @property
    def get_estado_display(self):
        """
        Devuelve la etiqueta legible del estado.
        """
        return {
            'pendiente': 'Pendiente',
            'pago_parcial': 'Pago Parcial',
            'pagado': 'Pagado',
            'vencido': 'Vencido'
        }.get(self.get_estado(), 'Desconocido')







    # documentos/models.py
    # documentos/models.py
    @property
    def get_dias_restantes(self):
        """
        Devuelve los días restantes hasta el vencimiento.
        - Usa solo la fecha (ignora completamente la hora).
        - Asegura consistencia de zona horaria.
        """
        # Zona horaria de Perú
        lima_tz = pytz.timezone('America/Lima')

        # Obtener la hora actual en Lima
        ahora = timezone.localtime(timezone.now(), lima_tz)
        hoy = ahora.date()

        # Asegurar que fecha_vencimiento esté en zona horaria de Lima
        if timezone.is_naive(self.fecha_vencimiento):
            # Si es naive, asumimos que es en Lima
            vencimiento_tz = lima_tz.localize(self.fecha_vencimiento)
        else:
            # Si tiene zona horaria, convierte a Lima
            vencimiento_tz = timezone.localtime(self.fecha_vencimiento, lima_tz)

        vencimiento = vencimiento_tz.date()

        return (vencimiento - hoy).days






    def get_dias_display(self):
        dias = self.get_dias_restantes
        if dias > 0:
            return f"{dias} días"
        elif dias == 0:
            return "Hoy"
        else:
            return f"{abs(dias)} días vencido"

    def get_absolute_url(self):
        return reverse('documentos:documento_detail', args=[str(self.id)])
    

    

    # documentos/models.py
    @property
    def get_dias_restantes_absoluto(self):
        """
        Devuelve el valor absoluto de los días restantes (para atraso).
        Si es -15 días, devuelve 15.
        """
        return abs(self.get_dias_restantes)