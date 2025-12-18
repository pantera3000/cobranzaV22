# cobros/models.py
import calendar  # ✅ Añade esta línea
from django.db import models
from documentos.models import Documento
from cobradores.models import Cobrador
from django.utils import timezone
from decimal import Decimal


from django.contrib.auth.models import User




# cobros/models.py

def localtime_peru():
    return timezone.localtime(timezone.now())






from datetime import datetime, time
from django.db.models import Sum
from decimal import Decimal
import pytz






class SecuenciaCorrelativo(models.Model):
    """
    Modelo para gestionar secuencias únicas de correlativos por año.
    Asegura que los números no se repitan, incluso si se eliminan cobros.
    """
    nombre = models.CharField(
        max_length=50,
        unique=True,
        help_text="Nombre único de la secuencia (ej: 'cobro')"
    )
    ultimo_correlativo = models.IntegerField(
        default=0,
        help_text="Último número de correlativo usado"
    )
    año = models.IntegerField(
        help_text="Año al que pertenece la secuencia"
    )

    class Meta:
        verbose_name = "Secuencia de Correlativo"
        verbose_name_plural = "Secuencias de Correlativos"
        unique_together = ('nombre', 'año')  # Evita duplicados

    def __str__(self):
        return f"{self.nombre} ({self.año}): {self.ultimo_correlativo}"






class PlanillaCierre(models.Model):
    cobrador = models.ForeignKey(Cobrador, on_delete=models.CASCADE)
    fecha = models.DateField(help_text="Día que se cierra la planilla")
    total_cobrado = models.DecimalField(max_digits=12, decimal_places=2, help_text="Total de cobros del día")
    total_depositado = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    estado = models.CharField(
        max_length=20,
        choices=[
            ('pendiente', 'Pendiente'),
            ('parcial', 'Parcial'),
            ('completado', 'Completado'),
        ],
        default='pendiente'
    )
    creada_en = models.DateTimeField(auto_now_add=True)
    actualizada_en = models.DateTimeField(auto_now=True)
    notas = models.TextField(blank=True, null=True, help_text="Notas generales del cierre")


    # En la clase PlanillaCierre
    actualizado_en = models.DateTimeField(null=True, blank=True)


    class Meta:
        unique_together = ('cobrador', 'fecha')
        verbose_name = "Planilla de Cierre"
        verbose_name_plural = "Planillas de Cierre"
        ordering = ['-fecha']

    def __str__(self):
        return f"{self.cobrador.nombre} - {self.fecha} ({self.estado})"

    @property
    def saldo_pendiente(self):
        return max(self.total_cobrado - self.total_depositado, Decimal('0.00'))

    def actualizar_estado(self):
        if self.total_depositado >= self.total_cobrado:
            self.estado = 'completado'
        elif self.total_depositado > 0:
            self.estado = 'parcial'
        else:
            self.estado = 'pendiente'
        self.save()










    def tiene_cobros_pendientes(self):
        """
        Verifica si hay cobros del mismo día que no fueron incluidos en el cierre.
        """
        # Convertir fecha local a datetime con zona horaria
        lima_tz = pytz.timezone('America/Lima')
        inicio_dia = lima_tz.localize(datetime.combine(self.fecha, time.min))
        fin_dia = lima_tz.localize(datetime.combine(self.fecha, time.max))

        # Calcular total de cobros del cobrador ese día
        cobros_del_dia = Cobro.objects.filter(
            cobrador=self.cobrador,
            fecha__gte=inicio_dia,
            fecha__lte=fin_dia
        ).aggregate(total=Sum('monto'))['total'] or Decimal('0.00')

        # Si el total registrado es menor al real → hay pagos faltantes
        return cobros_del_dia > self.total_cobrado





























class DepositoParcial(models.Model):
    planilla = models.ForeignKey(PlanillaCierre, on_delete=models.CASCADE)
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    fecha = models.DateTimeField(default=timezone.now)
    creado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    notas = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        verbose_name = "Depósito Parcial"
        verbose_name_plural = "Depósitos Parciales"
        ordering = ['-fecha']

    def __str__(self):
        return f"S/ {self.monto} - {self.planilla.cobrador.nombre}"










class Cobro(models.Model):
    # Opciones para tipo de pago
    TIPO_PAGO_CHOICES = [
        ('efectivo', 'Efectivo'),
        ('yape', 'Yape'),
        ('deposito', 'Depósito'),
        ('otro', 'Otro'),
    ]



    documento = models.ForeignKey(Documento, on_delete=models.CASCADE, verbose_name="Documento")
    cobrador = models.ForeignKey(Cobrador, on_delete=models.PROTECT, verbose_name="Cobrador")
    monto = models.DecimalField(
        max_digits=12, decimal_places=2,
        verbose_name="Monto Pagado (S/)"
    )
    fecha = models.DateTimeField(default=localtime_peru, verbose_name="Fecha del Pago")
    creado_en = models.DateTimeField(auto_now_add=True)

    # ✅ Nuevo campo: referencia del pago múltiple
    referencia = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Referencia / N° Operación",
        help_text="Número de recibo, transferencia, depósito, etc."
    )

    # ✅ Campo opcional: notas adicionales
    notas = models.CharField(
        max_length=60,
        blank=True,
        null=True,
        verbose_name="Notas Adicionales",
        help_text="Información extra sobre el pago (opcional). Máx. 60 caracteres."
    )



    # ✅ Nuevo campo: tipo de pago
    tipo_pago = models.CharField(
        max_length=20,
        choices=TIPO_PAGO_CHOICES,
        blank=True,
        null=True,
        verbose_name="Tipo de Pago"
    )



    correlativo = models.CharField(max_length=20, blank=True, null=True)  # ✅ Nuevo campo



    # ✅ CAMBIO CLAVE: Quién registró este pago en el sistema
    usuario_registro = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cobros_registrados',
        verbose_name="Registrado por",
        help_text="Usuario del sistema que registró este pago"
    )



    class Meta:
        verbose_name = "Cobro"
        verbose_name_plural = "Cobros"
        ordering = ['-fecha']

    def __str__(self):
        return f"Pago S/ {self.monto} - {self.documento.get_tipo_display()} {self.documento.get_numero_completo} - {self.fecha.strftime('%d/%m/%Y')}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Recalcular monto_pagado del documento
        total_cobros = self.documento.cobro_set.aggregate(
            total=models.Sum('monto')
        )['total'] or Decimal('0.00')
        self.documento.monto_pagado = total_cobros
        self.documento.save(update_fields=['monto_pagado'])

    def delete(self, *args, **kwargs):
        # Guardar datos antes de eliminar
        documento = self.documento
        fecha_pago = self.fecha.date() if isinstance(self.fecha, datetime) else self.fecha
        cobrador = self.cobrador

        # Eliminar el cobro (esto ya recalcula monto_pagado del documento)
        super().delete(*args, **kwargs)

        # Recalcular monto_pagado del documento
        total_cobros = documento.cobro_set.aggregate(
            total=models.Sum('monto')
        )['total'] or Decimal('0.00')
        documento.monto_pagado = total_cobros
        documento.save(update_fields=['monto_pagado'])

        # ✅ Recalcular total_cobrado en la planilla del día
        try:
            planilla = PlanillaCierre.objects.get(cobrador=cobrador, fecha=fecha_pago)
            inicio_dia = timezone.make_aware(datetime.combine(planilla.fecha, time.min))
            fin_dia = timezone.make_aware(datetime.combine(planilla.fecha, time.max))

            nuevo_total = Cobro.objects.filter(
                cobrador=cobrador,
                fecha__gte=inicio_dia,
                fecha__lte=fin_dia
            ).aggregate(total=Sum('monto'))['total'] or Decimal('0.00')

            planilla.total_cobrado = nuevo_total
            planilla.save()

            # Opcional: si hay actualizado_en y fue después del cierre original, podrías limpiarlo
            # Pero mejor dejarlo como historial

        except PlanillaCierre.DoesNotExist:
            pass  # No hay planilla para ese día




class MetaMensual(models.Model):
    mes = models.DateField(help_text="Primer día del mes, ej: 2025-09-01")
    monto_objetivo = models.DecimalField(max_digits=12, decimal_places=2)
    descripcion = models.CharField(max_length=200, blank=True, null=True)
    creada_en = models.DateTimeField(auto_now_add=True)
    actualizada_en = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('mes',)

    def __str__(self):
        return f"Meta {self.mes.strftime('%B %Y')}: S/ {self.monto_objetivo}"

    @property
    def monto_alcanzado(self):
        from .models import Cobro
        from django.db.models import Sum
        import datetime

        try:
            if not self.mes:
                return Decimal('0.00')

            primer_dia = self.mes
            _, last_day = calendar.monthrange(primer_dia.year, primer_dia.month)
            ultimo_dia = primer_dia.replace(day=last_day)

            fecha_inicio = timezone.make_aware(
                datetime.datetime.combine(primer_dia, datetime.time.min)
            )
            fecha_fin = timezone.make_aware(
                datetime.datetime.combine(ultimo_dia, datetime.time.max)
            )

            total = Cobro.objects.filter(
                fecha__gte=fecha_inicio,
                fecha__lte=fecha_fin
            ).aggregate(total=Sum('monto'))['total'] or Decimal('0.00')

            return total
        except Exception as e:
            print(f"Error en monto_alcanzado: {e}")
            return Decimal('0.00')

    @property
    def porcentaje_alcanzado(self):
        if self.monto_objetivo <= 0:
            return 0
        return min((self.monto_alcanzado / self.monto_objetivo) * 100, 100)