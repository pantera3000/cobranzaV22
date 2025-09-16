from django.contrib import admin
from .models import Cobro, PlanillaCierre, DepositoParcial, MetaMensual


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

    # Para no sobrecargar la edición
    raw_id_fields = ('documento',)

    # Orden predeterminado
    ordering = ['-fecha']

    # Campos de solo lectura
    readonly_fields = ('fecha', 'creado_en')

    # Mostrar cliente en la lista
    def get_cliente(self, obj):
        return obj.documento.cliente.nombre

    get_cliente.short_description = 'Cliente'
    get_cliente.admin_order_field = 'documento__cliente__nombre'



# ✅ Nuevo: Admin para PlanillaCierre
@admin.register(PlanillaCierre)
class PlanillaCierreAdmin(admin.ModelAdmin):
    list_display = (
        'cobrador',
        'fecha',
        'get_total_cobrado',
        'total_depositado',
        'saldo_pendiente',
        'estado',
        'creada_en'
    )
    list_filter = ('fecha', 'estado', 'cobrador')
    search_fields = ('cobrador__nombre', 'notas')
    readonly_fields = ('creada_en', 'actualizada_en', 'total_cobrado', 'saldo_pendiente')
    raw_id_fields = ('cobrador',)
    ordering = ['-fecha']

    def get_total_cobrado(self, obj):
        return f"S/ {obj.total_cobrado:,.2f}"
    get_total_cobrado.short_description = "Total Cobrado"
    get_total_cobrado.admin_order_field = 'total_cobrado'

    def saldo_pendiente(self, obj):
        return f"S/ {obj.saldo_pendiente:,.2f}"
    saldo_pendiente.short_description = "Pendiente"


# ✅ Nuevo: Admin para Depósito Parcial
@admin.register(DepositoParcial)
class DepositoParcialAdmin(admin.ModelAdmin):
    list_display = ('planilla', 'get_cobrador', 'monto', 'fecha', 'creado_por')
    list_filter = ('fecha', 'planilla__cobrador', 'creado_por')
    search_fields = ('planilla__cobrador__nombre', 'notas', 'planilla__fecha')
    readonly_fields = ('fecha', 'creado_por')
    raw_id_fields = ('planilla',)
    ordering = ['-fecha']

    def get_cobrador(self, obj):
        return obj.planilla.cobrador.nombre
    get_cobrador.short_description = "Cobrador"
    get_cobrador.admin_order_field = 'planilla__cobrador__nombre'



# Admin existente para MetaMensual
@admin.register(MetaMensual)
class MetaMensualAdmin(admin.ModelAdmin):
    list_display = ('mes', 'monto_objetivo', 'monto_alcanzado', 'porcentaje_alcanzado', 'descripcion')
    list_filter = ('mes',)
    search_fields = ('descripcion',)
    readonly_fields = ('monto_alcanzado', 'porcentaje_alcanzado')