from django import template

register = template.Library()


@register.filter
def durata(minutes):
    """Formatta una durata espressa in minuti: 94 -> "1 h 34 min"."""
    try:
        minutes = int(minutes)
    except (TypeError, ValueError):
        return ''
    hours, mins = divmod(minutes, 60)
    return f'{hours} h {mins:02d} min' if hours else f'{mins} min'
