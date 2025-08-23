# documentos/templatetags/url_filters.py
from django import template
from urllib.parse import urlencode

register = template.Library()

@register.simple_tag
def url_replace(request, **kwargs):
    """
    Reemplaza parámetros en la URL actual.
    Ejemplo: ?page=2&q=juan → ?page=3&q=juan
    """
    query = request.GET.copy()
    for key, value in kwargs.items():
        if value is not None and value != '' and value != 'None':
            query[key] = value
        else:
            query.pop(key, None)
    return query.urlencode()