from datetime import datetime, timedelta

from django import template

register = template.Library()


@register.simple_tag
def tomorrow_day():
    date_res = datetime.now() + timedelta(days=1)
    return date_res.strftime('%d/%m/%Y')


@register.filter(name='has_group')
def has_group(user, group_name):
    return user.groups.filter(name=group_name).exists()