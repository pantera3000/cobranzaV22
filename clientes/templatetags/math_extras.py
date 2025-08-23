# clientes/templatetags/math_extras.py
from django import template

register = template.Library()

@register.filter
def modulo(value):
    """
    Devuelve el valor absoluto de un número.
    Nombre 'modulo' para evitar conflicto con la función abs() de Python.
    """
    try:
        return abs(int(value))  # Aquí 'abs' es la función de Python, no el filtro
    except (ValueError, TypeError):
        return 0