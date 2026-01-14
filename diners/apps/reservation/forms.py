from datetime import datetime

from dal import autocomplete
from django import forms
from django.conf import settings
from django.contrib.admin import widgets
from django.core.cache import cache
from django.core.exceptions import NON_FIELD_ERRORS
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from requests import RequestException

from diners.utils import helpers
from .models import Reservation, Menu, ReservationCategory, Dish
from .widgets import DishesMultipleWidget

GRAPHQL_SERV = settings.GRAPHQL_SERVICE


class ReservationForm(forms.ModelForm):
    extra_data = forms.CharField(
        required=False,
        max_length=250,
        widget=forms.HiddenInput()
    )
    extra_diet = forms.CharField(
        required=False,
        max_length=250,
        widget=forms.HiddenInput()
    )
    area = autocomplete.Select2ListCreateChoiceField(
        required=True,
        label=_('area').capitalize(),
        widget=autocomplete.ListSelect2(url='admin:reservation_reservation_areacomplete'),
    )
    person = autocomplete.Select2ListCreateChoiceField(
        required=True,
        label=_('person').capitalize(),
        widget=autocomplete.ListSelect2(url='admin:reservation_reservation_personcomplete', forward=('area',)),
    )
    is_diet = forms.BooleanField(
        required=False,
        label=_('is diet').capitalize(),
        disabled=True,
    )

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request')
        super().__init__(*args, **kwargs)
        instance = self.instance

        # para ocultar el + para añadir platos en la reservacion
        self.fields['dishes'].widget.can_add_related = False

        if not self.request.user.has_perm('reservation.confirm_change_reservation'):
            self.fields['is_confirmed'].disabled = True

        difference = helpers.get_difference_day()
        menu_list = Menu.objects.filter(date__gte=difference)

        # modificando
        if instance.pk:
            if instance.person:
                resp = GRAPHQL_SERV.get_diner_api(instance.person)
                if resp and resp.ok:
                    diner = resp.json()['data']['dinerById']
                    person = diner['person']
                    area = person['area']
                    self.fields['area'].choices = [(area['id'], area['name'])]
                    self.fields['person'].choices = [(person['id'], person['name'])]
                    if diner:
                        menu = instance.menu
                        diner_close = helpers.report_time(menu)

                        self.fields['menu'].widget.can_add_related = False
                        self.fields['menu'].widget.can_change_related = False

                        if self.request.user.person:
                            if self.request.user.has_perm('reservation.all_change_reservation'):
                                # si pasa las 48 horas
                                if difference >= diner_close:
                                    self.fields['dishes'].disabled = True
                                    self.fields['is_confirmed'].disabled = True
                                    self.fields['menu'].queryset = Menu.objects.filter(pk=instance.menu.pk)
                                    self.fields['menu'].widget.can_add_related = False
                                    self.fields['menu'].widget.can_change_related = False
                                else:
                                    self.fields['menu'].queryset = menu_list
                                self.fields['area'].disabled = True
                                self.fields['person'].disabled = True
                                self.fields['menu'].disabled = True
                            elif self.request.user.has_perm('reservation.area_change_reservation'):
                                if difference >= diner_close or diner['paymentMethod'] == 'CP':
                                    self.fields['dishes'].disabled = True
                                    self.fields['is_confirmed'].disabled = True
                                    self.fields['menu'].queryset = Menu.objects.filter(pk=instance.menu.pk)
                                else:
                                    self.fields['menu'].queryset = menu_list
                                self.fields['area'].disabled = True
                                self.fields['person'].disabled = True
                                self.fields['menu'].disabled = True
                            elif self.request.user.has_perm('reservation.confirm_change_reservation'):
                                today = datetime.now()
                                diner_opening = helpers.confirm_start_time(menu)
                                diner_ending = helpers.confirm_end_time(menu)

                                dishes = menu.dishes
                                diet_dishes = menu.diet_dishes

                                if diner['isDiet']:
                                    is_liquid_menu = diet_dishes.filter(dish_category__option_number=8).first()
                                else:
                                    is_liquid_menu = dishes.filter(dish_category__option_number=8).first()

                                is_liquid_reserv = instance.dishes.filter(dish_category__option_number=8).first()

                                if diner_opening <= today < diner_ending and is_liquid_menu and not is_liquid_reserv:
                                    self.fields['area'].disabled = True
                                    self.fields['person'].disabled = True
                                    self.fields['menu'].queryset = Menu.objects.filter(pk=instance.menu.pk)
                                    self.fields['menu'].disabled = True

                                    exclude = dishes.exclude(dish_category__option_number=8)
                                    exclude_diet = diet_dishes.exclude(dish_category__option_number=8)

                                    disable = set()
                                    for elem in exclude:
                                        disable.add(elem.id)
                                    for elem in exclude_diet:
                                        disable.add(elem.id)

                                    self.fields['dishes'].widget.widget.disabled_choices = list(disable)
                                    self.fields['dishes'].widget.widget.attrs['data-disabled'] = 1
                                else:
                                    self.fields['area'].disabled = True
                                    self.fields['person'].disabled = True
                                    self.fields['dishes'].disabled = True
                                    self.fields['is_confirmed'].disabled = True
                                    self.fields['menu'].queryset = Menu.objects.filter(pk=instance.menu.pk)
                                    self.fields['menu'].disabled = True

                            self.initial['area'] = int(diner['person']['area']['id'])
                            self.fields['dishes'].queryset = instance.menu.diet_dishes.all() if diner[
                                'isDiet'] else instance.menu.dishes.all()
            else:
                self.fields['dishes'].disabled = True
                self.fields['is_confirmed'].disabled = True
                self.fields['menu'].queryset = Menu.objects.filter(pk=instance.menu.pk)
                self.fields['menu'].widget.can_add_related = False
                self.fields['menu'].widget.can_change_related = False
                self.fields['area'].disabled = True
                self.fields['person'].disabled = True
                self.fields['menu'].disabled = True
                self.fields['dishes'].queryset = instance.menu.dishes.all()
        # agregando
        else:
            # por defecto no muestra platos en la reserva
            self.fields['dishes'].queryset = Dish.objects.none()
            # si cuando se procesa la reserva existe un menu seleccionado
            if 'menu' in self.data and self.data.get('menu'):
                diet = (self.request.POST['extra_diet'] or 'false').lower()
                menu = Menu.objects.get(id=self.data.get('menu'))
                self.fields['dishes'].queryset = menu.diet_dishes.all() if diet == 'true' else menu.dishes.all()
            if self.request.user.person:
                # caso reservar a todos por área
                if self.request.user.has_perm('reservation.all_add_reservation'):
                    self.fields['area'].choices = cache.get('all-area')
                    self.fields['person'].choices = cache.get('all-person')
                # caso responsable por área
                elif self.request.user.has_perm('reservation.area_add_reservation'):
                    result, result_area = GRAPHQL_SERV.diners_advanced_to_person_area_choices(self.request.user.person)
                    self.fields['area'].choices = result_area
                    self.initial['area'] = result_area[0][0]
                    self.fields['area'].disabled = True
                    self.fields['person'].choices = result

                self.fields['menu'].queryset = menu_list

    def clean_menu(self):
        menu = self.cleaned_data['menu']
        today = datetime.now()

        combine_close = helpers.report_time(menu)
        difference = helpers.get_difference_day()
        if difference >= combine_close:
            raise forms.ValidationError(
                _('You can no longer reserve for %(date)s.'),
                params={'date': menu.__str__().lower()},
            )
        # si es sabado o domingo
        elif today.isoweekday() == 6 or today.isoweekday() == 7:
            raise forms.ValidationError(_('You can no longer reserve for Saturday or Sunday'))

        return menu

    def clean_dishes(self):
        dishes = self.cleaned_data['dishes']
        user = self.request.user
        if not user.is_superuser and user.has_perm('reservation.confirm_change_reservation'):
            instance = getattr(self, 'instance', None)
            if instance and instance.pk:
                return dishes.union(instance.dishes.all())
        return dishes
    class Meta:
        model = Reservation
        fields = [
            'extra_data',
            'extra_diet',
            'area',
            'person',
            'is_diet',
            'menu',
            'dishes',
            'is_confirmed',
        ]
        error_messages = {
            NON_FIELD_ERRORS: {
                'unique_together': _('The diner already has a reservation with that menu.')
            }
        }
        widgets = {
            'dishes': DishesMultipleWidget(attrs={'data-disabled': 0}),
        }

    class Media:
        js = ( 'js/api_conection.js', 'js/qr2.js', 'js/message.js', 'js/cookie.js', 'js/main_form.js',
              )


class ReservationCategoryAdminForm(forms.ModelForm):
    dining_room = autocomplete.Select2ListCreateChoiceField(
        required=False,
        label=_('dining room').capitalize(),
        widget=autocomplete.ListSelect2(url='admin:reservation_reservation_dinningroomcomplete'),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # si esta modificando, carga el comedor que se selecciono del listado
        if self.instance.pk:
            self.fields['dining_room'].choices = GRAPHQL_SERV.diningrooms_to_choices()

    def clean_dining_room(self):
        dining_room = self.cleaned_data['dining_room']
        if dining_room in [None, '']:
            dining_room = None
        return dining_room

    class Meta:
        model = ReservationCategory
        fields = ['name', 'dining_room', 'is_confirmable', 'is_active']


class DateReportForm(forms.Form):
    date_start = forms.DateField(
        required=True,
        label=_('date start').capitalize(),
        widget=widgets.AdminDateWidget()
    )
    date_end = forms.DateField(
        required=True,
        label=_('date end').capitalize(),
        widget=widgets.AdminDateWidget()
    )
    dining_room = autocomplete.Select2ListCreateChoiceField(
        required=True,
        label=_('dining room').capitalize(),
        widget=autocomplete.ListSelect2(url='admin:reservation_reservation_dinningroomcomplete'),
    )

    def clean(self):
        cleaned_data = super().clean()
        date_start = cleaned_data.get('date_start')
        date_end = cleaned_data.get('date_end')
        if date_start and date_end and date_start > date_end:
            raise forms.ValidationError(_('The start of the date must not exceed the end of the date.'))
        return cleaned_data

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['dining_room'].choices = GRAPHQL_SERV.diningrooms_to_choices()

    class Media:
        js = ('admin/js/core.js', 'js/cookie.js', 'js/api_conection.js', 'js/report_list.js',
              'js/jquery.modal.min.js')


class ActionFormMixins(forms.Form):
    person = autocomplete.Select2ListCreateChoiceField(
        required=True,
        label=_('person').capitalize(),
        widget=autocomplete.Select2Multiple(url='admin:reservation_reservation_personcomplete'),
    )

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)


class InviteOffPlanForm(ActionFormMixins):
    ubication = forms.ChoiceField(
        label=_('ubication').capitalize(),
        choices=[(1, _('inside').capitalize()), (2, _('outside').capitalize())],
        initial=1,
        widget=forms.RadioSelect(attrs={'class': 'radio-inline'}),
    )
    area = autocomplete.Select2ListCreateChoiceField(
        required=False,
        label=_('area').capitalize(),
        widget=autocomplete.ListSelect2(url='admin:reservation_reservation_areacomplete'),
    )
    person = autocomplete.Select2ListCreateChoiceField(
        required=False,
        label=_('person').capitalize(),
        widget=autocomplete.Select2Multiple(url='admin:reservation_reservation_personcomplete', forward=('area',)),
    )

    field_order = ['ubication', 'area', 'person']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        cache.set('all-area', GRAPHQL_SERV.areas_to_choices(), None)

    def clean_area(self):
        ubication = self.cleaned_data['ubication']
        area = self.cleaned_data['area']
        if ubication == '2' and area in [None, '']:
            raise forms.ValidationError(_('This field is required.'))
        return area

    def clean_person(self):
        ubication = self.cleaned_data['ubication']
        selected_diners = self.cleaned_data['person']
        if ubication == '1':
            if selected_diners in [None, '']:
                raise forms.ValidationError(_('This field is required.'))

            selected_diners = self.cleaned_data['person'].translate({91: None, 93: None, 39: None, 32: None}).split(',')
            select_action = self.data.getlist('_selected_action')

            datetime_now = datetime.now()
            time_now = datetime_now.time()

            len_invites = len(selected_diners)
            len_select_action = len(select_action)

            if len_select_action is not len_invites:
                raise forms.ValidationError(
                    _('You must select all people to reserv. {0} left.').format(len_select_action - len_invites)
                )

            is_selected = Q(id__in=select_action)
            # si no existe al menos una reservacion a confirmar
            if Reservation.objects.filter(is_selected).count() < len_select_action:
                raise forms.ValidationError(
                    _('At least a selected reservation does not exists. Try selecting others reservations again.'))

            reserv_in_time = Q(menu__date=datetime_now) & Q(
                menu__schedule__start_time__lte=time_now) & Q(
                menu__schedule__offplan_time__gt=time_now)

            is_reserv_selected_in_time = is_selected & reserv_in_time

            # si al menos una reservacion a confirmar no esta en tiempo
            if Reservation.objects.filter(is_reserv_selected_in_time).count() < len_select_action:
                raise forms.ValidationError(
                    _('At least a selected reservation is out of time. Try selecting others reservations again.'))

            diners_to_pay = []

            is_menu_in_time = Q(date=datetime_now) & Q(schedule__start_time__lte=time_now) & Q(
                schedule__offplan_time__gt=time_now)
            menu = Menu.objects.filter(is_menu_in_time).first()
            balance_menu = helpers.sum_price_dishes(menu.dishes.all())

            error_list = []
            is_invite_list = Q(reservation_category__name='Invitado')

            for id_person in selected_diners:
                try:
                    resp = GRAPHQL_SERV.get_diner_api(id_person)
                except RequestException:
                    raise forms.ValidationError(_('Connection error. Contact the system administrators.'))
                else:
                    if resp and resp.ok:
                        resp_json = resp.json()
                        diner = resp_json['data']['dinerById']
                        person = diner['person']
                        if 'errors' not in resp_json and diner:
                            # si tiene reservacion para hoy
                            if Reservation.objects.filter(Q(person=id_person) & reserv_in_time).first():
                                error_list.append(_('The diner {0} has reservation today.').format(person['name']))
                            # si ya reservo hoy como fuera de plan de otro invitado
                            elif Reservation.objects.filter(
                                    Q(offplan_data={
                                        'offplan_person': id_person}) & reserv_in_time & is_invite_list).first():
                                error_list.append(_('The diner {0} has reservation today for an invite.').format(
                                    person['name'])
                                )
                            # si ya reservo hoy como otro fuera de plan
                            elif Reservation.objects.filter(
                                    Q(offplan_data={'offplan_person': id_person}) & reserv_in_time).first():
                                error_list.append(_('The diner {0} has reservation today for an offplan.').format(
                                    person['name'])
                                )
                            else:
                                pay_method = diner['paymentMethod']
                                if pay_method == 'AP':
                                    andvanced_pay = person['advancepaymentRelated']
                                    if andvanced_pay:
                                        balance = float(andvanced_pay['balance'])
                                        if balance < balance_menu:
                                            error_list.append(_('The diner {0} has not enought balance.').format(
                                                person['name'])
                                            )
                                diners_to_pay.append({
                                    'id': id_person,
                                    'name': person['name'],
                                    'payment_method': pay_method,
                                    'position': person['position'],
                                    'to_pay': balance_menu
                                })
                        else:
                            error_list.append(
                                _('The balance of {0} is corrupted. It cannot confirm.').format(person['name']))

            if error_list:
                raise forms.ValidationError(
                    '<br>'.join(['<span>{0}</span>'.format(error) for error in error_list]))

            for din in diners_to_pay:
                if helpers.validate_pay(din['payment_method'], menu.schedule, menu.date.isoweekday(),
                                        din['position']):
                    try:
                        resp_transaction = GRAPHQL_SERV.create_transaction(
                            action='diners_reservation_reservation_confirm_offplan',
                            amount=float(balance_menu),
                            description=f'Se ha realizado una confirmación de reserva de invitado fuera de plan '
                                        f'a nombre de {din["name"]} '
                                        f'de {menu.schedule.name.lower()} con fecha {menu.format_date}.',
                            person=din['id'],
                            type='DB',
                            user=self.request.user.username
                        )
                    except RequestException:
                        raise forms.ValidationError(
                            _('Connection error. Contact the system administrators.')
                        )
                    else:
                        trans_json = resp_transaction.json()['data']['createTransaction']['transaction']
                        din['id_transaction'] = trans_json['id']
                        din['to_pay'] = trans_json['resultingBalance']

            selected_diners = diners_to_pay
        return selected_diners

    class Media:
        js = ('js/cookie.js', 'js/jquery.modal.min.js', 'js/message.js', 'js/api_conection.js', 'js/invite_off_plan.js')
        css = {'all': ('css/jquery.modal.min.css', 'css/actions.css', 'css/radio_inline.css')}


class DonateForm(ActionFormMixins):
    count = forms.ChoiceField(
        label=_('count').capitalize(),
        choices=[(1, _('one').capitalize()), (2, _('all').capitalize())],
        initial=2,
        widget=forms.RadioSelect(attrs={'class': 'radio-inline'}),
    )
    person_unique = autocomplete.Select2ListCreateChoiceField(
        required=False,
        label=_('person').capitalize(),
        widget=autocomplete.Select2Multiple(attrs={'data-maximum-selection-length': 1},
                                            url='admin:reservation_reservation_personcomplete'),
    )
    person = autocomplete.Select2ListCreateChoiceField(
        required=False,
        label=_('person').capitalize(),
        widget=autocomplete.Select2Multiple(url='admin:reservation_reservation_personcomplete'),
    )

    field_order = ['count', 'person', 'person_unique']

    def clean_person(self):
        count = self.data['count']
        selected_diners = self.cleaned_data['person']

        if count == '2':
            if selected_diners in [None, '']:
                raise forms.ValidationError(_('This field is required.'))

            selected_diners = self.cleaned_data['person'].translate({91: None, 93: None, 39: None, 32: None}).split(',')
            select_action = self.data.getlist('_selected_action')

            datetime_now = datetime.now()
            time_now = datetime_now.time()

            len_invites = len(selected_diners)
            len_select_action = len(select_action)

            if len_select_action is not len_invites:
                raise forms.ValidationError(
                    _('You must select all people to reserv. {0} left.').format(len_select_action - len_invites)
                )

            is_selected = Q(id__in=select_action)
            # si no existe al menos una reservacion a confirmar
            if Reservation.objects.filter(is_selected).count() < len_select_action:
                raise forms.ValidationError(
                    _('At least a selected reservation does not exists. Try selecting others reservations again.'))

            reserv_in_time = Q(menu__date=datetime_now) & Q(
                menu__schedule__start_time__lte=time_now) & Q(
                menu__schedule__end_time__gt=time_now)

            is_reserv_selected_in_time = is_selected & reserv_in_time

            # si al menos una reservacion a confirmar no esta en tiempo
            if Reservation.objects.filter(is_reserv_selected_in_time).count() < len_select_action:
                raise forms.ValidationError(
                    _('At least a selected reservation is out of time. Try selecting others reservations again.'))

            error_list = []

            for id_person, id_reserv in zip(selected_diners, select_action):
                try:
                    resp = GRAPHQL_SERV.get_diner_api(id_person)
                except RequestException:
                    raise forms.ValidationError(_('Connection error. Contact the system administrators.'))
                else:
                    if resp and resp.ok:
                        resp_json = resp.json()
                        diner = resp_json['data']['dinerById']
                        person = diner['person']
                        if 'errors' not in resp_json and diner:
                            # si es donativo de su propia reserva
                            if Reservation.objects.filter(Q(id=id_reserv) & reserv_in_time).first().person == int(
                                    id_person):
                                error_list.append(
                                    _('The diner {0} cannot donate by self.').format(person['name']))
            if error_list:
                raise forms.ValidationError('<br>'.join(['<span>{0}</span>'.format(error) for error in error_list]))
        return selected_diners

    def clean_person_unique(self):
        count = self.data['count']
        selected_diners = self.cleaned_data['person_unique']

        if count == '1':
            if selected_diners in [None, '']:
                raise forms.ValidationError(_('This field is required.'))

            selected_diners = self.cleaned_data['person_unique'].translate(
                {91: None, 93: None, 39: None, 32: None}).split(',')
            select_action = self.data.getlist('_selected_action')

            datetime_now = datetime.now()
            time_now = datetime_now.time()

            len_select_action = len(select_action)

            is_selected = Q(id__in=select_action)
            # si no existe al menos una reservacion a confirmar
            if Reservation.objects.filter(is_selected).count() < len_select_action:
                raise forms.ValidationError(
                    _('At least a selected reservation does not exists. Try selecting others reservations again.'))

            reserv_in_time = Q(menu__date=datetime_now) & Q(
                menu__schedule__start_time__lte=time_now) & Q(
                menu__schedule__end_time__gt=time_now)

            is_reserv_selected_in_time = is_selected & reserv_in_time

            # si al menos una reservacion a confirmar no esta en tiempo
            if Reservation.objects.filter(is_reserv_selected_in_time).count() < len_select_action:
                raise forms.ValidationError(
                    _('At least a selected reservation is out of time. Try selecting others reservations again.'))

            error_list = []

            for id_reserv in select_action:
                try:
                    resp = GRAPHQL_SERV.get_diner_api(selected_diners[0])
                except RequestException:
                    raise forms.ValidationError(_('Connection error. Contact the system administrators.'))
                else:
                    if resp and resp.ok:
                        resp_json = resp.json()
                        diner = resp_json['data']['dinerById']
                        person = diner['person']
                        if 'errors' not in resp_json and diner:
                            # si es donativo de su propia reserva
                            if Reservation.objects.filter(Q(id=id_reserv) & reserv_in_time).first().person == \
                                    int(selected_diners[0]):
                                error_list.append(
                                    _('The diner {0} cannot donate by self.').format(person['name']))
            if error_list:
                raise forms.ValidationError('<br>'.join(['<span>{0}</span>'.format(error) for error in error_list]))
        return selected_diners

    class Media:
        js = ('js/cookie.js', 'js/jquery.modal.min.js', 'js/message.js', 'js/api_conection.js', 'js/donate.js')
        css = {'all': ('css/jquery.modal.min.css', 'css/actions.css', 'css/radio_inline.css')}


class OffPlanForm(ActionFormMixins):
    ubication = forms.ChoiceField(
        label=_('ubication').capitalize(),
        choices=[(1, _('inside').capitalize()), (2, _('outside').capitalize())],
        initial=1,
        widget=forms.RadioSelect(attrs={'class': 'radio-inline'}),
    )
    area = autocomplete.Select2ListCreateChoiceField(
        required=False,
        label=_('area').capitalize(),
        widget=autocomplete.ListSelect2(url='admin:reservation_reservation_areacomplete'),
    )
    person = autocomplete.Select2ListCreateChoiceField(
        required=False,
        label=_('person').capitalize(),
        widget=autocomplete.Select2Multiple(url='admin:reservation_reservation_personcomplete', forward=('area',)),
    )

    field_order = ['ubication', 'area', 'person']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        cache.set('all-area', GRAPHQL_SERV.areas_to_choices(), None)

    def clean_area(self):
        ubication = self.cleaned_data['ubication']
        area = self.cleaned_data['area']
        if ubication == '2' and area in [None, '']:
            raise forms.ValidationError(_('This field is required.'))
        return area

    def clean_person(self):
        ubication = self.cleaned_data['ubication']
        selected_diners = self.cleaned_data['person']
        if ubication == '1':
            if selected_diners in [None, '']:
                raise forms.ValidationError(_('This field is required.'))

            selected_diners = self.cleaned_data['person'].translate({91: None, 93: None, 39: None, 32: None}).split(',')
            select_action = self.data.getlist('_selected_action')

            datetime_now = datetime.now()
            time_now = datetime_now.time()

            len_invites = len(selected_diners)

            len_select_action = len(select_action)

            if len_select_action is not len_invites:
                raise forms.ValidationError(
                    _('You must select all people to reserv. {0} left.').format(len_select_action - len_invites)
                )

            is_selected = Q(id__in=select_action)
            # si no existe al menos una reservacion a confirmar
            if Reservation.objects.filter(is_selected).count() < len_select_action:
                raise forms.ValidationError(
                    _('At least a selected reservation does not exists. Try selecting others reservations again.'))

            reserv_in_time = Q(menu__date=datetime_now) & Q(
                menu__schedule__end_time__lte=time_now) & Q(
                menu__schedule__offplan_time__gt=time_now)

            is_reserv_selected_in_time = is_selected & reserv_in_time

            # si al menos una reservacion a confirmar no esta en tiempo
            if Reservation.objects.filter(is_reserv_selected_in_time).count() < len_select_action:
                raise forms.ValidationError(
                    _('At least a selected reservation is out of time. Try selecting others reservations again.'))

            error_list = []
            is_invite_list = Q(reservation_category__name='Invitado')

            for id_person in selected_diners:
                try:
                    resp = GRAPHQL_SERV.get_diner_api(id_person)
                except RequestException:
                    raise forms.ValidationError(_('Connection error. Contact the system administrators.'))
                else:
                    if resp and resp.ok:
                        resp_json = resp.json()
                        diner = resp_json['data']['dinerById']
                        person = diner['person']
                        if 'errors' not in resp_json and diner:
                            # si tiene reservacion para hoy y se confirmó su propia reserva
                            if Reservation.objects.filter(
                                    Q(person=id_person) & reserv_in_time & Q(is_confirmed=True)).first():
                                error_list.append(
                                    _('The diner {0} has confirmed reservation today.').format(person['name']))
                            # si ya reservo hoy como fuera de plan de otro invitado
                            elif Reservation.objects.filter(Q(offplan_data={
                                'offplan_person': id_person}) & reserv_in_time & is_invite_list).first():
                                error_list.append(_('The diner {0} has reservation today for an invite.').format(
                                    person['name'])
                                )
                            # si ya reservo hoy como otro fuera de plan
                            elif Reservation.objects.filter(
                                    Q(offplan_data={'offplan_person': id_person}) & reserv_in_time).first():
                                error_list.append(_('The diner {0} has reservation today for an offplan.').format(
                                    person['name'])
                                )
            if error_list:
                raise forms.ValidationError('<br>'.join(['<span>{0}</span>'.format(error) for error in error_list]))
        return selected_diners

    class Media:
        js = ('js/cookie.js', 'js/jquery.modal.min.js', 'js/message.js', 'js/api_conection.js', 'js/off_plan.js')
        css = {'all': ('css/jquery.modal.min.css', 'css/actions.css', 'css/radio_inline.css')}
