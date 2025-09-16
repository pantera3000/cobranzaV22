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
    

@register.filter
def mul(value, arg):
    """Multiplica el valor por el argumento"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0
    


@register.filter
def sub(value, arg):
    """Resta el argumento al valor"""
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return 0