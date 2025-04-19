from django import template
from django.forms.widgets import CheckboxInput

register = template.Library()


@register.filter
def is_checkbox(field):
    """
    Vérifie si le champ du formulaire utilise une widget CheckboxInput.
    """
    return isinstance(field.field.widget, CheckboxInput)
