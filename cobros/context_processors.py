from .models import MetaMensual
from django.utils import timezone

def meta_mensual(request):
    """
    Añade la meta mensual actual al contexto global
    """
    try:
        today = timezone.now().date()
        meta = MetaMensual.objects.get(mes__year=today.year, mes__month=today.month)
        return {'meta': meta}
    except MetaMensual.DoesNotExist:
        return {'meta': None}
    except Exception as e:
        # Evita que un error aquí rompa toda la app
        print(f"Error en context_processor meta_mensual: {e}")
        return {'meta': None}
    



def menu_context(request):
    puede_ver_reparto = False

    if request.user.is_authenticated:
        puede_ver_reparto = (
            # ✅ Grupos permitidos: añade aquí los que quieras
            request.user.groups.filter(name__in=[
                'Repartidores', 
                'Encargados Reparto', 
                'Staff Local',
                'Supervisores'
                'Admin'
            ]).exists() or
            
            # ✅ Usuarios específicos (opcional)
            request.user.username in ['juanc', 'adminaqp', 'VALERIA']
        )

    return {
        'es_repartidor': puede_ver_reparto
    }