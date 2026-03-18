from django import template

register = template.Library()


@register.filter(name='score_class')
def score_class(score):
    """Return CSS class based on score"""
    try:
        score = int(score)
        if score >= 80:
            return 'score-excellent'
        elif score >= 60:
            return 'score-good'
        elif score >= 40:
            return 'score-fair'
        else:
            return 'score-poor'
    except (ValueError, TypeError):
        return 'score-unknown'


@register.filter(name='density_class')
def density_class(density):
    """Return CSS class for keyword density"""
    try:
        density = float(density)
        if 0.5 <= density <= 2.5:
            return 'text-success'
        elif density < 0.5:
            return 'text-warning'
        else:
            return 'text-danger'
    except (ValueError, TypeError):
        return ''


@register.filter(name='multiply')
def multiply(value, arg):
    """Multiply value by arg"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0