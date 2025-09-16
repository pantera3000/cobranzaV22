from django.contrib import admin
from .models import Cobrador

@admin.register(Cobrador)
class CobradorAdmin(admin.ModelAdmin):
    # ✅ Mostrar el campo 'user' en la lista
    list_display = ('nombre', 'dni', 'telefono', 'correo', 'user', 'creado_en')
    
    # ✅ Permitir buscar por nombre, DNI y usuario
    search_fields = ('nombre', 'dni', 'user__username', 'user__first_name', 'user__last_name')
    
    # ✅ Filtros laterales (incluye si tiene usuario asignado)
    list_filter = ('creado_en', 'user')
    
    # ✅ Orden alfabético por nombre
    ordering = ('nombre',)
    
    # ✅ Mejorar la vista del formulario
    fieldsets = (
        ('Información Personal', {
            'fields': ('nombre', 'dni', 'telefono', 'correo', 'direccion')
        }),
        ('Usuario del Sistema', {
            'fields': ('user',),
            'description': 'Vincula este cobrador con un usuario de acceso. Si no se asigna, no podrá usar funciones como el cierre de planilla.'
        }),
    )
    
    # ✅ Campos de solo lectura
    readonly_fields = ('creado_en', 'actualizado_en')