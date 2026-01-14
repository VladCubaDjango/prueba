import datetime

from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.utils import formats
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django_extensions.db.fields.json import JSONField
from django.dispatch import receiver
from django.db.models.signals import pre_save, post_save

from diners.utils.helpers import price_dishes, sorted_by_option_number, html_dishes, get_difference_day
from diners.utils.mixins import NameMixin, CreationModificationDateMixin, ActivationMixin

min_type_dish = settings.MIN_NUMBER_TYPE_DISHES
max_type_dish = settings.MAX_NUMBER_TYPE_DISHES

min_id_person = settings.MIN_NUMBER_ID_PERSON
max_id_person = settings.MAX_NUMBER_ID_PERSON

GRAPHQL_SERV = settings.GRAPHQL_SERVICE


class DishCategory(NameMixin, CreationModificationDateMixin):
    option_number = models.PositiveIntegerField(
        validators=[MinValueValidator(min_type_dish), MaxValueValidator(max_type_dish)],
        verbose_name=_('option number'),
        help_text=_('This number must be between {min} and {max}.').format(min=min_type_dish, max=max_type_dish),
        primary_key=True
    )

    class Meta:
        ordering = ['option_number']
        verbose_name = _('dish category')
        verbose_name_plural = _('dish categories')


class Dish(NameMixin, CreationModificationDateMixin):
    dish_category = models.ForeignKey(
        DishCategory,
        verbose_name=_('dish category'),
        on_delete=models.CASCADE,
    )
    price = models.DecimalField(
        validators=[MaxValueValidator(18.00)],
        verbose_name=_('price'),
        max_digits=4,
        decimal_places=2
    )

    @property
    def as_html(self):
        return mark_safe('%s (<strong>$%s</strong>)' % (self.name, self.price))

    def __str__(self):
        return '%s - $%s' % (self.name, self.price)

    class Meta:
        ordering = ['dish_category__option_number']
        verbose_name = _('dish')
        verbose_name_plural = _('dishes')


class DishMixin(models.Model):
    dishes = models.ManyToManyField(
        Dish,
        verbose_name=_('dishes'),
    )

    @property
    def payment_dishes(self):
        return price_dishes(self.dishes.all())

    @property
    def sorted_dishes(self):
        return sorted_by_option_number(self.dishes.all())

    @property
    def dishes_as_html(self):
        return html_dishes(self.sorted_dishes)

    payment_dishes.fget.short_description = _('full payment')
    sorted_dishes.fget.short_description = _('dishes')
    dishes_as_html.fget.short_description = _('dishes($)')

    class Meta:
        abstract = True


class MealSchedule(NameMixin):
    start_time = models.TimeField(
        verbose_name=_('start time'),
        default=datetime.time(00, 00, 00)
    )
    end_time = models.TimeField(
        verbose_name=_('end time'),
        default=datetime.time(00, 00, 00)
    )
    offplan_time = models.TimeField(
        verbose_name=_('offplan time'),
        default=datetime.time(00, 00, 00)
    )
    report_time = models.TimeField(
        verbose_name=_('report time'),
        default=datetime.time(00, 00, 00)
    )
    is_payment = models.BooleanField(
        verbose_name=_('is payment'),
        default=False,
    )

    class Meta:
        ordering = ['-id']
        verbose_name = _('meal schedule')
        verbose_name_plural = _('meals schedules')


class Menu(DishMixin, CreationModificationDateMixin):
    diet_dishes = models.ManyToManyField(
        Dish,
        related_name='diet_menu',
        verbose_name=_('diet dishes'),
    )
    schedule = models.ForeignKey(
        MealSchedule,
        verbose_name=_('schedule'),
        on_delete=models.CASCADE,
    )
    date = models.DateField(
        verbose_name=_('date'),
    )

    @property
    def payment_dishes_diet(self):
        return price_dishes(self.diet_dishes.all())

    @property
    def sorted_dishes_diet(self):
        return sorted_by_option_number(self.diet_dishes.all())

    @property
    def dishes_as_html_diet(self):
        return html_dishes(self.sorted_dishes_diet)

    @property
    def full_menu(self):
        regular = self.sorted_dishes
        regular.extend(self.sorted_dishes_diet)
        return sorted_by_option_number(list(set(regular)))

    @property
    def full_menu_as_html(self):
        return html_dishes(self.full_menu)

    @property
    def format_date(self):
        return '{}'.format(formats.date_format(self.date, format='l j \d\e F \d\e Y'))

    payment_dishes_diet.fget.short_description = _('full diet payment')
    sorted_dishes_diet.fget.short_description = _('dishes of diet')
    dishes_as_html_diet.fget.short_description = _('dishes of diet($)')

    def __str__(self):
        return '{}, {}'.format(self.schedule, formats.date_format(self.date, format='l j \d\e F \d\e Y'))

    class Meta:
        ordering = ['-date', '-schedule__id']
        verbose_name = _('menu')
        verbose_name_plural = _('menus')
        constraints = [models.UniqueConstraint(fields=['date', 'schedule'], name='unique menu')]


class User(models.Model):
    user_id = models.PositiveIntegerField(
        validators=[MinValueValidator(min_id_person), MaxValueValidator(max_id_person)],
        verbose_name=_('user'),
    )

    def __str__(self):
        return '{0} {1}'.format(_('user').capitalize(), self.user_id)

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')


class ReservationCategory(NameMixin, ActivationMixin):
    meal_schedules = models.ManyToManyField(MealSchedule, through='ReservCatSchedule')
    dining_room = models.IntegerField(
        verbose_name=_('dining room'),
        blank=True,
        null=True,
    )
    is_confirmable = models.BooleanField(
        verbose_name=_('is confirmable'),
        default=False,
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _('reservation category')
        verbose_name_plural = _('reservation categories')


class ReservCatSchedule(ActivationMixin):
    mealschedule = models.ForeignKey(
        MealSchedule,
        verbose_name=_('schedule'),
        on_delete=models.CASCADE)
    reservation_category = models.ForeignKey(
        ReservationCategory,
        verbose_name=_('reservation category'),
        on_delete=models.CASCADE)
    count_diners = models.PositiveIntegerField(
        validators=[MinValueValidator(min_id_person), MaxValueValidator(max_id_person)],
        verbose_name=_('count diners'),
    )

    def __str__(self):
        return self.mealschedule.name + ' de ' + self.reservation_category.name

    class Meta:
        ordering = ['mealschedule__id']
        verbose_name = _('meal schedule')
        verbose_name_plural = _('meals schedules')
        constraints = [models.UniqueConstraint(fields=['mealschedule', 'reservation_category'], name='unique category')]


@receiver(post_delete, sender=ReservCatSchedule)
def reservcatschedule_post_delete(sender, instance, **kwargs):
    Reservation.objects.filter(
        reservation_category=instance.reservation_category,
        menu__schedule=instance.mealschedule,
        menu__date__gte=get_difference_day()
    ).delete()


class Reservation(DishMixin, CreationModificationDateMixin):
    person = models.PositiveIntegerField(
        validators=[MinValueValidator(min_id_person), MaxValueValidator(max_id_person)],
        verbose_name=_('person'),
        blank=True,
        null=True,
    )
    reservation_category = models.ForeignKey(
        ReservationCategory,
        verbose_name=_('reservation category'),
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    person_donate = models.PositiveIntegerField(
        validators=[MinValueValidator(min_id_person), MaxValueValidator(max_id_person)],
        verbose_name=_('donate'),
        blank=False,
        null=True,
    )
    menu = models.ForeignKey(
        Menu,
        verbose_name=_('menu'),
        on_delete=models.CASCADE,
    )
    reserv_log_user = models.CharField(
        verbose_name=_('reserved by'),
        max_length=250,
        default='',
    )
    modify_log_user = models.ManyToManyField(
        User,
        verbose_name=_('updated by'),
        blank=True,
    )
    confirm_log_user = models.CharField(
        verbose_name=_('confirmed by'),
        max_length=250,
        default='',
    )
    offplan_data = JSONField(
        default=[],
        verbose_name=_('offplan information'),
    )
    is_confirmed = models.BooleanField(
        verbose_name=_('is confirmed'),
        default=False
    )

    @property
    def get_person(self):
        return self.person

    @property
    def get_area(self):
        return self.person

    def __str__(self):
        return _('Reservation for {0} on {1}').format(
            self.get_person or self.reservation_category, formats.date_format(self.menu.date)
        )

    class Meta:
        ordering = ['-id']
        verbose_name = _('reservation')
        verbose_name_plural = _('reservations')
        constraints = [models.UniqueConstraint(fields=['person', 'menu'], name='unique reservation')]
        permissions = (
            ('all_view_reservation', _('Can view all reserves')),
            ('area_view_reservation', _('Can view all reserves from same area')),
            ('all_add_reservation', _('Can add all reserves')),
            ('area_add_reservation', _('Can add all reserves from same area')),
            ('all_change_reservation', _('Can change all reserves')),
            ('confirm_change_reservation', _('Can change all reserves from the day')),
            ('area_change_reservation', _('Can change all reserves from same area')),
            ('all_delete_reservation', _('Can delete all reserves')),
            ('area_delete_reservation', _('Can delete all reserves from same area')),
            ('view_report', _('Can view report')),
            ('view_operation', _('Can view operation')),
            ('view_camera', _('Can view camera')),
            ('confirm_after_hours', _('Can confirm after hours')),
        )


@receiver(post_save, sender=Menu)
def change_menu(sender, instance, **kwargs):
    if not kwargs.get('created', False):
        print(instance)
        # from diners.apps.reservation.models import Reservation
        # from diners.apps.reservation.models import Menu
        # from diners.utils.helpers import sum_price_dishes
        # from django.conf import settings
        # from django.db.models import Q
        #
        # GRAPHQL_SERV = settings.GRAPHQL_SERVICE
        #
        # menus = [
        #     1982,
        #     1983,
        #     1985,
        #     1986,
        # ]
        # for menu in menus:
        #     real_menu = Menu.objects.get(id=menu)
        #     condition = Q(menu=real_menu)
        #     reservations = Reservation.objects.filter(condition)
        #
        #     for reservation in reservations:
        #         price_to_change = 0
        #         for dish in reservation.dishes.all():
        #             if dish not in real_menu.dishes.all():
        #                 new_dish = None
        #                 for elem in real_menu.dishes.all():
        #                     if dish.dish_category == elem.dish_category:
        #                         new_dish=elem
        #                 if new_dish==None:
        #                     price_to_change = price_to_change-dish.price
        #                     reservation.dishes.remove(dish)
        #                 else:
        #                     price_to_change = price_to_change+dish.price-new_dish.price
        #                     reservation.dishes.remove(dish)
        #                     reservation.dishes.add(new_dish)
        #         if price_to_change < 0:
        #             trans_type = 'DB'
        #             price_to_change = price_to_change*-1
        #         elif price_to_change > 0:
        #             trans_type = 'CR'
        #         id = reservation.person
        #         if id !=None:
        #             diner = GRAPHQL_SERV.get_diner_api(id).json()['data']['dinerById']
        #             payment_method = diner['paymentMethod']
        #             if payment_method == 'AP' and price_to_change!=0:
        #                 try:
        #                     GRAPHQL_SERV.create_transaction(
        #                         action='diners_reservation_reservation_change_menu',
        #                         amount=float(price_to_change),
        #                         description='Cambio de platos autorizado por Yamicela, Jefa del Comedor',
        #                         person=id,
        #                         type=trans_type,
        #                         user='admin'
        #                     )
        #                 except:
        #                     print(id+" -------- "+str(price_to_change))


class Operation(models.Model):
    id = models.PositiveBigIntegerField(primary_key=True, unique=True)
    reservation = models.ForeignKey(
        Reservation,
        on_delete=models.CASCADE,
        blank=False,
        null=False,
    )

    def __str__(self):
        return '{0} {1}'.format(_('Operation').capitalize(), self.id)

    class Meta:
        verbose_name = _('Operation')
        verbose_name_plural = _('Operation')
