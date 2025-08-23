# reportes/templatetags/reportes_filters.py
from django import template

register = template.Library()

@register.filter
def sum(queryset, attr):
    """Suma un atributo en una lista de objetos"""
    try:
        return sum(getattr(item, attr) for item in queryset)
    except (TypeError, AttributeError):
        return 0

@register.filter
def avg(queryset, attr):
    """Promedio de un atributo en una lista de objetos"""
    try:
        values = [getattr(item, attr) for item in queryset if getattr(item, attr) is not None]
        return int(sum(values) / len(values)) if values else 0
    except (TypeError, AttributeError, ZeroDivisionError):
        return 0