from django import template

register = template.Library()


@register.filter
def durata(minutes):
    try:
        minutes = int(minutes)
    except (TypeError, ValueError):
        return ''
    hours, mins = divmod(minutes, 60)
    return f'{hours} h {mins:02d} min' if hours else f'{mins} min'
