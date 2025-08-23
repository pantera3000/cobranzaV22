from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from .models import Documento
from clientes.models import Cliente
from cobradores.models import Cobrador


# Filtro personalizado para Estado
class EstadoFilter(SimpleListFilter):
    title = 'Estado'
    parameter_name = 'estado'

    def lookups(self, request, model_admin):
        return [
            ('pagado', 'Pagado'),
            ('pendiente', 'Pendiente'),
            ('vencido', 'Vencido'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'pagado':
            return queryset.filter(monto_total__lte=models.F('monto_pagado') + models.F('monto_devolucion'))
        elif self.value() == 'pendiente':
            return queryset.exclude(monto_total__lte=models.F('monto_pagado') + models.F('monto_devolucion')).filter(fecha_vencimiento__gte=timezone.now())
        elif self.value() == 'vencido':
            return queryset.exclude(monto_total__lte=models.F('monto_pagado') + models.F('monto_devolucion')).filter(fecha_vencimiento__lt=timezone.now())
        return queryset


# Admin principal
@admin.register(Documento)
class DocumentoAdmin(admin.ModelAdmin):
    list_display = (
        'get_tipo_display', 'get_numero_completo', 'cliente',
        'monto_total', 'monto_pagado', 'monto_devolucion',
        'get_saldo_pendiente', 'get_estado', 'get_dias_restantes',
        'fecha_emision', 'fecha_vencimiento'
    )
    list_filter = ('tipo', EstadoFilter, 'fecha_emision', 'fecha_vencimiento', 'cliente')
    search_fields = ('numero', 'serie', 'cliente__nombre', 'cliente__dni_ruc')
    date_hierarchy = 'fecha_emision'
    raw_id_fields = ('cliente', 'cobrador')
    ordering = ['-fecha_emision']

    def get_tipo_display(self, obj):
        return obj.get_tipo_display()
    get_tipo_display.short_description = 'Tipo'

    def get_numero_completo(self, obj):
        return f"{obj.serie}-{obj.numero}" if obj.serie else obj.numero
    get_numero_completo.short_description = 'Número'

    def get_saldo_pendiente(self, obj):
        return f"S/ {obj.get_saldo_pendiente():,.2f}"
    get_saldo_pendiente.short_description = 'Saldo'

    def get_estado(self, obj):
        estado = obj.get_estado()
        if estado == 'pagado':
            return 'Pagado'
        elif estado == 'vencido':
            return 'Vencido'
        else:
            return 'Pendiente'
    get_estado.short_description = 'Estado'
    get_estado.admin_order_field = 'fecha_vencimiento'  # Solo para ordenar por fecha, no por estado real

    def get_dias_restantes(self, obj):
        dias = obj.get_dias_restantes()
        if dias > 0:
            return f"{dias} días"
        elif dias == 0:
            return "Hoy"
        else:
            return f"{abs(dias)} días vencido"
    get_dias_restantes.short_description = 'Días'


# Asegúrate de importar models y timezone
from django.db import models
from django.utils import timezone