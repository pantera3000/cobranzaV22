from django import template

register = template.Library()

@register.filter
def get_item_by_id(queryset, id):
    """
    Devuelve el objeto del queryset con el id dado
    Uso: {{ queryset|get_item_by_id:id }}
    """
    try:
        return queryset.get(id=id)
    except:
        return None