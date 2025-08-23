from django.contrib import admin
from .models import Cobro


@admin.register(Cobro)
class CobroAdmin(admin.ModelAdmin):
    # Campos que se muestran en la lista
    list_display = (
        'documento',
        'get_cliente',
        'monto',
        'cobrador',
        'fecha',
        'referencia',
        'creado_en'
    )

    # Filtros laterales
    list_filter = (
        'fecha',
        'cobrador',
        'documento__cliente',
        'documento__tipo',
        'referencia'  # ✅ Filtro por referencia
    )

    # Campos para búsqueda
    search_fields = (
        'documento__numero',
        'documento__cliente__nombre',
        'documento__cliente__dni_ruc',
        'cobrador__nombre',
        'referencia'  # ✅ Buscar por referencia
    )

    # Jerarquía de fechas (arriba de la lista)
    date_hierarchy = 'fecha'

    # Para no sobrecargar la edición (si hay muchos documentos)
    raw_id_fields = ('documento',)

    # Orden predeterminado
    ordering = ['-fecha']

    # Campos de solo lectura en el formulario de edición
    readonly_fields = ('fecha', 'creado_en')

    # Mostrar cliente en la lista (viene del documento)
    def get_cliente(self, obj):
        return obj.documento.cliente.nombre

    get_cliente.short_description = 'Cliente'
    get_cliente.admin_order_field = 'documento__cliente__nombre'