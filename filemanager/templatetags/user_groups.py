from django import template

register = template.Library()

STAFF_GROUP_NAMES = [
    'IT Staff',
    'Security Analyst',
    'Account Support Team',
    'Security Team',
    'Network Administrator',
    'Admin',
]


@register.filter
def is_staff_or_support_group(user):
    if not getattr(user, 'is_authenticated', False):
        return False
    return user.is_staff or user.groups.filter(name__in=STAFF_GROUP_NAMES).exists()
