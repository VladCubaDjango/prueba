from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ReservationConfig(AppConfig):
    name = 'diners.apps.reservation'
    verbose_name = _('Reservation')
    verbose_name_plural = _('Reservations')
