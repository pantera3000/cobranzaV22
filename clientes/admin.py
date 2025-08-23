from django.contrib import admin
from .models import Cliente

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'dni_ruc', 'telefono', 'correo', 'creado_en')
    search_fields = ('nombre', 'dni_ruc')
    list_filter = ('creado_en',)
    ordering = ('nombre',)