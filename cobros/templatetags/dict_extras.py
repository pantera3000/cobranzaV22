# cobros/templatetags/dict_extras.py
from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Obtiene un valor de un diccionario por clave"""
    return dictionary.get(key)