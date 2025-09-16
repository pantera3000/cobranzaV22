# documentos/utils.py
def get_user_roles(request):
    """Devuelve un dict con los roles del usuario"""
    es_repartidor = request.user.groups.filter(name='Repartidores').exists()
    # Añade usuarios específicos como repartidores
    if not es_repartidor:
        es_repartidor = request.user.username in ['maria_cobrador', 'otro_usuario']
    
    es_encargado = request.user.groups.filter(name='Encargados Reparto').exists()
    puede_crear_reporte = request.user.groups.filter(name='Puede Crear Reportes').exists()

    return {
        'es_repartidor': es_repartidor,
        'es_encargado': es_encargado,
        'puede_crear_reporte': puede_crear_reporte,
    }