# cobros/utils.py
from django.utils import timezone
from django.db import transaction
from .models import SecuenciaCorrelativo

def localtime_peru():
    return timezone.localtime(timezone.now())

@transaction.atomic
def generar_correlativo():
    hoy = localtime_peru().date()
    año = hoy.year

    secuencia, created = SecuenciaCorrelativo.objects.select_for_update().get_or_create(
        nombre='cobro',
        año=año,
        defaults={'ultimo_correlativo': 0}
    )

    secuencia.ultimo_correlativo += 1
    secuencia.save()

    return f"{año}-{secuencia.ultimo_correlativo:05d}"