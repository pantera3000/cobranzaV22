from django.contrib import admin
from .models import Devolucion

@admin.register(Devolucion)
class DevolucionAdmin(admin.ModelAdmin):
    list_display = (
        'documento', 'get_cliente', 'monto',
        'cobrador', 'fecha', 'creado_en'
    )
    list_filter = ('fecha', 'cobrador', 'documento__cliente', 'documento__tipo')
    search_fields = (
        'documento__numero',
        'documento__cliente__nombre',
        'documento__cliente__dni_ruc',
        'cobrador__nombre'
    )
    date_hierarchy = 'fecha'
    raw_id_fields = ('documento',)
    ordering = ['-fecha']

    def get_cliente(self, obj):
        return obj.documento.cliente.nombre
    get_cliente.short_description = 'Cliente'
    get_cliente.admin_order_field = 'documento__cliente__nombre'