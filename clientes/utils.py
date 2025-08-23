# clientes/utils.py
from .models import LogActividad
from django.contrib.auth.models import User
from cobradores.models import Cobrador

def registrar_log(usuario=None, cobrador=None, categoria='', accion='', descripcion=''):
    """
    Registra una acción en el log de actividades.
    Puedes pasar usuario (User) o cobrador (Cobrador).
    """
    LogActividad.objects.create(
        usuario=usuario,
        cobrador=cobrador,
        categoria=categoria,
        accion=accion,
        descripcion=descripcion[:500]
    )