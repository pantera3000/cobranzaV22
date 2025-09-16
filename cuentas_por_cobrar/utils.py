# documentos/utils.py
from django.contrib.auth.models import User

def get_user_roles(request):
    """
    Devuelve un diccionario con los roles del usuario.
    Útil para pasar a cualquier contexto en vistas.
    """
    # Verifica si pertenece al grupo 'Repartidores'
    es_repartidor = request.user.groups.filter(name='Repartidores').exists()
    
    # Usuarios específicos que también actúan como repartidores
    usuarios_especiales = ['maria_cobrador', 'otro_usuario']  # ⚠️ Cambia según necesites
    if not es_repartidor and request.user.username in usuarios_especiales:
        es_repartidor = True

    es_encargado = request.user.groups.filter(name='Encargados Reparto').exists()
    puede_crear_reporte = request.user.groups.filter(name='Puede Crear Reportes').exists()

    return {
        'es_repartidor': es_repartidor,
        'es_encargado': es_encargado,
        'puede_crear_reporte': puede_crear_reporte,
    }