from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

min_id_person = settings.MIN_NUMBER_ID_PERSON
max_id_person = settings.MAX_NUMBER_ID_PERSON


class User(AbstractUser):


    person = models.PositiveIntegerField(
        validators=[MinValueValidator(min_id_person), MaxValueValidator(max_id_person)],
        verbose_name=_('person'),
        blank=True,
        null=True,
    )

    class Meta(AbstractUser.Meta):
        constraints = [models.UniqueConstraint(fields=['person'], name='unique person')]

        permissions = (
            ('can_view_diners', _('Can view diner(s)')),
            ('all_view_diners', _('Can view all diners')),
            ('area_view_diners', _('Can view all diners from same area')),
        )
