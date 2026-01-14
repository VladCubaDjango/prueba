from django.db import models
from django.utils.translation import gettext_lazy as _


class NameMixin(models.Model):
    name = models.CharField(
        verbose_name=_('name'),
        max_length=250,
        default='',
    )

    def __str__(self):
        return self.name

    class Meta:
        abstract = True


class ActivationMixin(models.Model):
    is_active = models.BooleanField(
        verbose_name=_('is active'),
        default=True
    )

    class Meta:
        abstract = True


class CreationModificationDateMixin(models.Model):
    creation_date = models.DateTimeField(
        verbose_name=_('creation date'),
        auto_now_add=True,
    )
    modification_date = models.DateTimeField(
        verbose_name=_('modification date'),
        auto_now=True,
    )

    class Meta:
        abstract = True
