# cobros/templatetags/custom_filters.py
from django import template

register = template.Library()

@register.filter
def div(value, arg):
    """
    Divide el valor por el argumento.
    Uso: {{ value|div:arg }}
    """
    try:
        return float(value) / float(arg)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0