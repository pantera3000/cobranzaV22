from django.db import models
from django.urls import reverse
from clientes.models import Cliente
from cobradores.models import Cobrador
from django.core.validators import MinValueValidator
from decimal import Decimal
from django.utils import timezone
import pytz
from django.contrib.auth.models import User


# Zona horaria de Perú
def localtime_peru():
    return timezone.localtime(timezone.now())


# Tipos de documentos
TIPO_DOCUMENTO_CHOICES = [
    ('factura', 'Factura'),
    ('boleta', 'Boleta'),
    ('nota_pedido', 'Nota de Pedido'),
    ('nota_venta', 'Nota de Venta'),
    ('otro', 'Otro'),
]


class Documento(models.Model):
    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.CASCADE,
        verbose_name="Cliente"
    )
    cobrador = models.ForeignKey(
        Cobrador,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Cobrador"
    )
    tipo = models.CharField(
        max_length=20,
        choices=TIPO_DOCUMENTO_CHOICES,
        verbose_name="Tipo"
    )
    serie = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name="Serie"
    )
    numero = models.CharField(
        max_length=20,
        verbose_name="Número"
    )
    fecha_emision = models.DateTimeField(
        default=localtime_peru,
        verbose_name="Fecha de Emisión"
    )
    fecha_vencimiento = models.DateTimeField(
        verbose_name="Fecha de Vencimiento"
    )
    monto_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Monto Total"
    )
    monto_pagado = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Monto Pagado"
    )
    monto_devolucion = models.DecimalField(
        max_digits=12,
        decimal_places=2,
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

    # --- Métodos principales ---

    def get_numero_completo(self):
        """Devuelve Serie-Número o solo Número si no hay serie"""
        if self.serie:
            return f"{self.serie}-{self.numero}"
        return self.numero

    def get_saldo_pendiente(self):
        """Saldo pendiente = total - pagado - devolución"""
        return self.monto_total - self.monto_pagado - self.monto_devolucion

    def get_estado(self):
        """
        Devuelve el estado del documento:
        - 'pagado': saldo <= 0
        - 'vencido': vencido y saldo > 0
        - 'pago_parcial': tiene pagos pero aún tiene saldo
        - 'pendiente': no pagado y no vencido
        """
        saldo = self.get_saldo_pendiente()
        ahora = localtime_peru()

        if saldo <= 0:
            return 'pagado'
        if self.fecha_vencimiento < ahora:
            return 'vencido'
        if self.monto_pagado > 0:
            return 'pago_parcial'
        return 'pendiente'

    @property
    def get_estado_display(self):
        """Etiqueta legible del estado"""
        return {
            'pendiente': 'Pendiente',
            'pago_parcial': 'Pago Parcial',
            'pagado': 'Pagado',
            'vencido': 'Vencido'
        }.get(self.get_estado(), 'Desconocido')

    @property
    def get_estado_badge_class(self):
        """Clase CSS para badge según estado"""
        return {
            'pagado': 'success',
            'vencido': 'danger',
            'pago_parcial': 'info',
            'pendiente': 'warning'
        }.get(self.get_estado(), 'secondary')

    # --- Días hasta vencimiento ---

    @property
    def get_dias_restantes(self):
        """
        Devuelve los días restantes (solo fecha, sin hora).
        Usa zona horaria de Lima.
        """
        lima_tz = pytz.timezone('America/Lima')
        hoy = timezone.localtime(timezone.now(), lima_tz).date()

        if timezone.is_naive(self.fecha_vencimiento):
            vencimiento = lima_tz.localize(self.fecha_vencimiento).date()
        else:
            vencimiento = timezone.localtime(self.fecha_vencimiento, lima_tz).date()

        return (vencimiento - hoy).days

    def get_dias_display(self):
        dias = self.get_dias_restantes
        if dias > 0:
            return f"{dias} días"
        elif dias == 0:
            return "Hoy"
        else:
            return f"{abs(dias)} días vencido"

    @property
    def get_dias_restantes_absoluto(self):
        """Valor absoluto de días restantes (para mostrar atraso)"""
        return abs(self.get_dias_restantes)

    # --- URL ---

    def get_absolute_url(self):
        return reverse('documentos:documento_detail', args=[str(self.id)])

    # --- MÉTODO CLAVE: Mantener montos sincronizados ---
    
    def actualizar_montos(self):
        """
        Recalcula monto_pagado y monto_devolucion desde los modelos relacionados.
        Debe llamarse después de crear/eliminar Cobro o Devolucion.
        """
        from cobros.models import Cobro
        from devoluciones.models import Devolucion

        total_cobros = Cobro.objects.filter(documento=self).aggregate(
            total=models.Sum('monto')
        )['total'] or Decimal('0.00')

        total_devoluciones = Devolucion.objects.filter(documento=self).aggregate(
            total=models.Sum('monto')
        )['total'] or Decimal('0.00')

        cambios = False
        if self.monto_pagado != total_cobros:
            self.monto_pagado = total_cobros
            cambios = True
        if self.monto_devolucion != total_devoluciones:
            self.monto_devolucion = total_devoluciones
            cambios = True

        if cambios:
            self.save(update_fields=['monto_pagado', 'monto_devolucion'])


# === MODELOS DE DESPACHO ===

class Despacho(models.Model):
    """
    Reporte diario de documentos asignados a un repartidor.
    Creado por un encargado o admin.
    """
    fecha = models.DateField(auto_now_add=True)
    repartidor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name="Repartidor"
    )
    creado_por = models.ForeignKey(
        User,
        related_name='despachos_creados',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Creado por"
    )
    estado = models.CharField(
        max_length=20,
        choices=[
            ('abierto', 'Abierto'),
            ('cerrado', 'Cerrado')
        ],
        default='abierto',
        verbose_name="Estado"
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Despacho"
        verbose_name_plural = "Despachos"
        unique_together = ('fecha', 'repartidor')  # Un solo despacho por día por repartidor
        ordering = ['-fecha', 'repartidor__username']

    def __str__(self):
        return f"Despacho {self.fecha} - {self.repartidor.get_full_name() or self.repartidor.username}"

    @property
    def total_enviado(self):
        """Suma el monto_total de todos los documentos asignados."""
        return sum(d.documento.monto_total for d in self.detalles.all())
    


    
    

    @property
    def total_cobrado_real(self):
        """
        Suma REAL de cobros registrados en el sistema (tabla Cobro)
        para los documentos incluidos en este despacho.
        Usa la referencia "REPARTO-{fecha}" o cualquier otro criterio si cambia.
        """
        from cobros.models import Cobro
        documento_ids = self.detalles.values_list('documento__id', flat=True)
        return Cobro.objects.filter(
            documento__id__in=documento_ids,
            fecha__date=self.fecha  # Asegura que sea del mismo día
        ).aggregate(total=models.Sum('monto'))['total'] or Decimal('0.00')

    @property
    def saldo_pendiente_real(self):
        return self.total_enviado - self.total_cobrado_real




    @property
    def total_cobrado(self):
        """Suma lo que el repartidor registró como cobrado."""
        return sum(d.cobrado for d in self.detalles.all())

    @property
    def saldo_pendiente(self):
        """Lo que falta por cobrar después del reparto."""
        return self.total_enviado - self.total_cobrado


class DetalleDespacho(models.Model):
    """
    Cada documento incluido en el despacho.
    Aquí se registra lo cobrado por el repartidor.
    """
    despacho = models.ForeignKey(
        Despacho,
        on_delete=models.CASCADE,
        related_name='detalles'
    )
    documento = models.ForeignKey(
        'Documento',  # Con comillas para evitar import circular
        on_delete=models.CASCADE
    )
    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.CASCADE
    )
    numero_pedido = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="N° Pedido"
    )
    notas = models.TextField(
        blank=True,
        null=True,
        verbose_name="Notas"
    )

    # Campos que llena el repartidor al final del día
    cobrado = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Cobrado"
    )
    medio_pago = models.CharField(
        max_length=20,
        choices=[
            ('efectivo', 'Efectivo'),
            ('yape', 'Yape / Plin'),
            ('transferencia', 'Transferencia'),
            ('deposito', 'Depósito Bancario'),
            ('credito', 'Crédito'),
            ('otro', 'Otro')
        ],
        blank=True,
        null=True,
        verbose_name="Medio de Pago"
    )
    observaciones = models.TextField(
        blank=True,
        null=True,
        verbose_name="Observaciones"
    )

    class Meta:
        verbose_name = "Detalle de Despacho"
        verbose_name_plural = "Detalles de Despacho"

    def __str__(self):
        return f"{self.documento} → {self.cliente}"