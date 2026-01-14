from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class PeopleConfig(AppConfig):
    name = 'diners.apps.people'
    verbose_name = _('People')
    verbose_name_plural = _('People')
