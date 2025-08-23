# cobradores/templatetags/custom_filters.py
from django import template

register = template.Library()

@register.filter
def absolute(value):
    """
    Devuelve el valor absoluto de un número.
    Uso: {{ value|absolute }}
    """
    try:
        return abs(float(value))
    except (ValueError, TypeError):
        return 0