from django import template

register = template.Library()

@register.filter
def slugify_badge(value):
    if not value:
        return ""
    return value.lower().replace(" ", "_")