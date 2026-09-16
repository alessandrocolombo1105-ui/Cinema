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


@register.filter
def stagger(index, step=0.06):
    try:
        return f'{int(index) * float(step):.2f}'
    except (TypeError, ValueError):
        return '0'
