from django.db import models
from documentos.models import Documento
from cobradores.models import Cobrador
from django.utils import timezone

def localtime_peru():
    return timezone.localtime(timezone.now())





class Devolucion(models.Model):
    documento = models.ForeignKey(Documento, on_delete=models.CASCADE, verbose_name="Documento")
    cobrador = models.ForeignKey(Cobrador, on_delete=models.PROTECT, verbose_name="Cobrador")
    monto = models.DecimalField(
        max_digits=12, decimal_places=2,
        verbose_name="Monto de Devolución (S/)"
    )
    fecha = models.DateTimeField(default=localtime_peru, verbose_name="Fecha de Devolución")
    creado_en = models.DateTimeField(auto_now_add=True)


    

    notas = models.CharField(
        max_length=60,
        blank=True,
        null=True,
        verbose_name="Notas Adicionales",
        help_text="Información extra sobre la devolución (opcional). Máx. 60 caracteres."
    )



    class Meta:
        verbose_name = "Devolución"
        verbose_name_plural = "Devoluciones"
        ordering = ['-fecha']

    def __str__(self):
        return f"Devolución S/ {self.monto} - {self.documento} - {self.fecha.strftime('%d/%m/%Y')}"