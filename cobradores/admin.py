from django.contrib import admin
from .models import Cobrador

@admin.register(Cobrador)
class CobradorAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'dni', 'telefono', 'correo', 'creado_en')
    search_fields = ('nombre', 'dni')
    list_filter = ('creado_en',)
    ordering = ('nombre',)