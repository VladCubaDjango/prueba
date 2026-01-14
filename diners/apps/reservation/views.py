import copy
import json
from datetime import datetime
from decimal import Decimal
from urllib.parse import quote as urlquote

from dal import autocomplete
from decouple import config
from django.conf import settings
from django.contrib import messages
from django.contrib.admin.utils import quote
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.paginator import Paginator
from django.db import Error, transaction
from django.db.models import Q
from django.http import JsonResponse, HttpResponseForbidden, HttpResponseBadRequest, QueryDict
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils import formats
from django.utils.decorators import method_decorator
from django.utils.html import format_html
from django.utils.translation import gettext as _, ngettext, gettext_lazy as _
from django.views import View
from django.views.generic import FormView, TemplateView
from requests.exceptions import RequestException

from diners.utils import helpers
from diners.utils.helpers import reservation_message, get_difference_day, confirm_start_time, confirm_end_time, \
    report_time, validate_pay, pay_until_top, message_payment
from .filters import ReservationFilter
from .forms import ReservationForm, InviteOffPlanForm, DonateForm, OffPlanForm
from .models import Operation, MealSchedule, ReservationCategory, Menu
from .models import Reservation
from .models import User
from .utils import isConfirmedHtmlList, moreActionReservationHtml, getQuerySetReservation, getActionsReservations

GRAPHQL_SERV = settings.GRAPHQL_SERVICE


class ReservationView(View):
    extra_context = None
    template_name = 'reservation/reservation_form.html'

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get(self, request, *args, **kwargs):
        extra_context = self.extra_context
        object_id = extra_context['object_id']
        user = request.user

        extra_context['show_save_and_add_another'] = True
        extra_context['show_save_and_continue'] = False
        extra_context['show_reset'] = True

        # si se esta modificando
        if object_id:
            reservation = Reservation.objects.get(pk=object_id)
            extra_context['original'] = reservation
            if reservation.person:
                resp = GRAPHQL_SERV.get_diner_api(reservation.person)
                if resp and resp.ok:
                    resp_json = resp.json()
                    if 'errors' in resp_json:
                        # self.message_user(request, resp_json['errors'][0]['message'], messages.ERROR)
                        messages.error(self.request, resp_json['errors'][0]['message'])
                        extra_context['show_save_and_add_another'] = False
                        extra_context['show_reset'] = False
                    else:
                        diner = resp_json['data']['dinerById']
                        if diner:
                            class_alert, msg = message_payment(diner)
                            menu = reservation.menu
                            if request.user:
                                difference = get_difference_day()
                                diner_close = report_time(menu)

                                person = diner['person']
                                name = person['name']
                                pay_method = diner['paymentMethod']
                                balance = person['advancepaymentRelated']['balance']
                                position = person['position'] or ''

                                extra_context['extra_data'] = ','.join(
                                    [name, pay_method, balance, position, class_alert])
                                extra_context['operations'] = reservation.operation_set.all()

                                extra_context['is_diet'] = diner['isDiet']
                                # si tiene permiso de editar todas las reservaciones
                                if request.user.has_perm('reservation.all_change_reservation'):
                                    extra_context['show_save_and_add_another'] = False
                                    # si pasa de las 48 horas
                                    if difference >= diner_close:
                                        extra_context['show_reset'] = False
                                        extra_context['show_delete'] = False
                                    else:
                                        extra_context['show_save_and_continue'] = True
                                        # self.message_user(request, format_html(msg), level=class_alert)
                                        messages.add_message(request, getattr(messages.constants, class_alert.upper()),
                                                             format_html(msg))
                                # si tiene permiso de editar todas las reservaciones del area
                                elif request.user.has_perm('reservation.area_change_reservation'):
                                    extra_context['show_save_and_add_another'] = False
                                    # si pasa de las 48 horas
                                    if difference >= diner_close or diner['paymentMethod'] == 'CP':
                                        extra_context['show_reset'] = False
                                        extra_context['show_delete'] = False
                                    else:
                                        extra_context['show_save_and_continue'] = True
                                        # self.message_user(request, format_html(msg), level=class_alert)
                                        messages.add_message(request, getattr(messages.constants, class_alert.upper()),
                                                             format_html(msg))
                                # si tiene permiso de editar la reservacion en el dia
                                elif request.user.has_perm('reservation.confirm_change_reservation'):
                                    today = datetime.now()
                                    diner_opening = confirm_start_time(menu)
                                    diner_ending = confirm_end_time(menu)

                                    if diner['isDiet']:
                                        is_liquid_menu = menu.diet_dishes.filter(
                                            dish_category__option_number=8).first()
                                    else:
                                        is_liquid_menu = menu.dishes.filter(dish_category__option_number=8).first()

                                    is_liquid_reserv = reservation.dishes.filter(
                                        dish_category__option_number=8).first()

                                    # si esta en el rango de apertura de comedor en el dia y hay en el menu normal o
                                    # de dieta al menos un liquido y no hay seleccionado en la reservacion un liquido
                                    if diner_opening <= today < diner_ending and is_liquid_menu and not is_liquid_reserv:
                                        extra_context['show_save_and_continue'] = True
                                        extra_context['show_reset'] = False
                                        alert_message = 'Una vez elegido el liquido, no se puede ' \
                                                        'revertir la selección.'
                                        # self.message_user(request, format_html(msg), level=class_alert)
                                        # self.message_user(request, format_html(alert_message), level='warning')
                                        messages.add_message(request, getattr(messages.constants, class_alert.upper()),
                                                             format_html(msg))
                                        messages.add_message(request, messages.WARNING, format_html(alert_message))
                                    else:
                                        extra_context['show_save_and_add_another'] = False
                                        extra_context['show_reset'] = False
                                        extra_context['show_delete'] = False
            else:
                extra_context['show_save_and_add_another'] = False
                extra_context['show_reset'] = False
                extra_context['show_delete'] = False
        else:
            cache.set('all-area', GRAPHQL_SERV.areas_to_choices(), None)
            cache.set('all-person', GRAPHQL_SERV.diners_to_choices(), None)

        form = ReservationForm(instance=Reservation.objects.get(pk=object_id),
                               request=request) if object_id else ReservationForm(request=request)

        view = TemplateView.as_view(
            template_name=self.template_name,
            extra_context={**self.extra_context, **{'form': form}}
        )
        return view(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        view = ReservationFormView.as_view(
            template_name=self.template_name,
            extra_context=self.extra_context,
        )
        return view(request, *args, **kwargs)


class ReservationFormView(FormView):
    model = Reservation
    form_class = ReservationForm
    object_id = None
    message = ''
    success = ''
    operation = ''
    __temp_reserv = None
    __temp_person_name = None
    __pay_method = ''
    __balance = ''
    __position = ''
    __transaction_id = None

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        print("Usuario: " + str(form.data['extra_data']) + " || Menu: " + str(form.data['menu']) + " || Fecha: " + str(
            datetime.now()))
        if form.is_valid() and self.confirm_reserv_validate(form) and self.is_process_pay(form):
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        self.object_id = self.extra_context['object_id']
        if self.object_id:
            self.__temp_reserv = self.model.objects.get(pk=self.object_id)
            kwargs['instance'] = copy.deepcopy(self.__temp_reserv)
        return kwargs

    def confirm_reserv_validate(self, form):
        validate = False
        if 'is_confirmed' in form.changed_data:
            menu = form.cleaned_data['menu']
            combine_ope = helpers.confirm_start_time(menu)
            combine_end = helpers.confirm_end_time(menu)
            difference = datetime.now()
            if combine_ope <= difference < combine_end:
                validate = True
            else:
                if form.cleaned_data['is_confirmed']:
                    self.message = 'No se puede confirmar por estar fuera de horario para esta reservación'
                else:
                    self.message = 'No se puede desconfirmar por estar fuera de horario para esta reservación'
                form.add_error('__all__', self.message)
        else:
            validate = True

        return validate

    def is_process_pay(self, form):
        is_correct = False
        dishes = form.cleaned_data['dishes']
        # id = form.cleaned_data['person']
        extra_data = form.cleaned_data['extra_data'].split(',')

        self.__temp_person_name = extra_data[0]
        pay_method = extra_data[1]
        self.__balance = extra_data[2]
        position = extra_data[3]
        if pay_method == 'CP':
            is_correct = True
        elif pay_method == 'AP':
            amount = helpers.to_money(extra_data[2])
            total_price = helpers.to_money(sum([d.price for d in dishes]))
            menu = form.cleaned_data['menu']
            # user = self.request.user.username
            # si el menu se paga y si no es sabado ni domingo
            if helpers.validate_pay(pay_method, menu.schedule, menu.date.isoweekday(), position):
                # si se esta modificando
                if self.object_id:
                    current_total_price = helpers.to_money(sum([d.price for d in self.__temp_reserv.dishes.all()]))
                    # type_transaction = ''
                    # result = 0
                    # dif = 0
                    if current_total_price == total_price:
                        self.success, self.message = helpers.success_message(amount)
                        is_correct = True
                    else:
                        # debito
                        if current_total_price < total_price:
                            dif = helpers.pay_until_top(total_price) - current_total_price
                            # type_transaction = 'DB'
                            # result = amount - dif
                        # credito
                        elif current_total_price > total_price:
                            dif = helpers.pay_until_top(current_total_price) - total_price
                            # type_transaction = 'CR'
                            # result = amount + dif

                        if amount + current_total_price >= total_price:
                            pass
                            is_correct = True

                            # description = f'Ha modificado una reservación de {menu.schedule.name.lower()} con ' \
                            #               f'fecha {menu.format_date}.'
                            # try:
                            #     transaction_json = GRAPHQL_SERV.create_transaction(
                            #         action='diners_reservation_reservation_update',
                            #         amount=float(dif),
                            #         description=description,
                            #         person=id,
                            #         type=type_transaction,
                            #         user=user
                            #     )
                            #     resp_json = transaction_json.json()
                            #     # si se efectuo correctamente la transaccion
                            #     if transaction_json.ok and 'errors' not in resp_json:
                            #         resp_trans = resp_json['data']['createTransaction']['transaction']
                            #         self.__transaction_id = resp_trans['id']
                            #         self.success, self.message = helpers.success_message(result)
                            #         self.__balance = result
                            #         self.operation = {
                            #             'id': resp_trans['id'],
                            #             'datetime': resp_trans['datetime'],
                            #             'type': resp_trans['type'],
                            #             'amount': resp_trans['amount'],
                            #         }
                            #         is_correct = True
                            #     else:
                            #         self.message = resp_json['errors'][0]['message']
                            #         form.add_error('__all__', self.message)
                            # except RequestException:
                            #     self.message = _('Connection error. Contact the system administrators.')
                            #     form.add_error('__all__', self.message)
                        else:
                            self.message = _('The advance payment is not enough.')
                            form.add_error('__all__', self.message)
                # si se esta agregando
                else:
                    total_price = helpers.pay_until_top(total_price)
                    if amount >= total_price:
                        # dif = amount - total_price
                        # description = f'Ha realizado una reservación de {menu.schedule.name.lower()} con fecha' \
                        #               f' {menu.format_date}.'
                        # try:
                        #     transaction_json = GRAPHQL_SERV.create_transaction(
                        #         action='diners_reservation_reservation_create',
                        #         amount=float(total_price),
                        #         description=description,
                        #         person=id,
                        #         type='DB',
                        #         user=user
                        #     )
                        #     resp_json = transaction_json.json()
                        #     # si se efectuo correctamente la transaccion
                        #     if transaction_json.ok and 'errors' not in resp_json:
                        #         self.__transaction_id = resp_json['data']['createTransaction']['transaction']['id']
                        #         self.success, self.message = helpers.success_message(dif)
                        #         self.__balance = dif
                        #         is_correct = True
                        #     else:
                        #         self.message = resp_json['errors'][0]['message']
                        #         form.add_error('__all__', self.message)
                        # except RequestException:
                        #     self.message = _('Connection error. Contact the system administrators.')
                        #     form.add_error('__all__', self.message)
                        is_correct = True
                    else:
                        self.message = _('The advance payment is not enough ($%s).') % (amount)
                        form.add_error('__all__', self.message)
            else:
                is_correct = True
        self.__pay_method = pay_method
        self.__position = position

        return is_correct

    def get_success_url(self):
        return None

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.accepts('text/html'):
            return response
        else:
            sid = transaction.savepoint()
            object = form.save(commit=False)
            object.reservation_category = ReservationCategory.objects.filter(meal_schedules__isnull=True).first()
            if not self.object_id:
                object.reserv_log_user = str(self.request.user)

            if 'is_confirmed' in form.changed_data:
                object.confirm_log_user = str(self.request.user)
            object.save()

            object.modify_log_user.add(User.objects.create(user_id=self.request.user.id))
            form.save()
            # ----------------------------------------------------------------------------
            id = form.cleaned_data['person']
            dishes = form.cleaned_data['dishes']
            extra_data = form.cleaned_data['extra_data'].split(',')
            pay_method = extra_data[1]
            position = extra_data[3]
            if pay_method == 'AP':
                amount = helpers.to_money(extra_data[2])
                total_price = helpers.to_money(sum([d.price for d in dishes]))
                menu = form.cleaned_data['menu']
                user = self.request.user.username
                # si el menu se paga y si no es sabado ni domingo
                if helpers.validate_pay(pay_method, menu.schedule, menu.date.isoweekday(), position):
                    # si se esta modificando
                    if self.object_id:
                        current_total_price = helpers.to_money(sum([d.price for d in self.__temp_reserv.dishes.all()]))
                        type_transaction = ''
                        result = 0
                        dif = 0
                        if current_total_price != total_price:
                            if current_total_price < total_price:
                                dif = helpers.pay_until_top(total_price) - current_total_price
                                type_transaction = 'DB'
                                result = amount - dif
                            # credito
                            elif current_total_price > total_price:
                                dif = helpers.pay_until_top(current_total_price) - total_price
                                type_transaction = 'CR'
                                result = amount + dif

                            description = f'Ha modificado una reservación de {menu.schedule.name.lower()} con ' \
                                          f'fecha {menu.format_date}.'
                            try:
                                transaction_json = GRAPHQL_SERV.create_transaction(
                                    action='diners_reservation_reservation_update',
                                    amount=float(dif),
                                    description=description,
                                    person=id,
                                    type=type_transaction,
                                    user=user
                                )
                                resp_json = transaction_json.json()
                                # si se efectuo correctamente la transaccion
                                if transaction_json.ok and 'errors' not in resp_json:
                                    resp_trans = resp_json['data']['createTransaction']['transaction']
                                    self.__transaction_id = resp_trans['id']
                                    self.success, self.message = helpers.success_message(result)
                                    self.__balance = result
                                    self.operation = {
                                        'id': resp_trans['id'],
                                        'datetime': resp_trans['datetime'],
                                        'type': resp_trans['type'],
                                        'amount': resp_trans['amount'],
                                    }
                                else:
                                    transaction.savepoint_rollback(sid)
                                    self.message = resp_json['errors'][0]['message']
                                    form.add_error('__all__', self.message)
                                    errors = form.errors
                                    message = ngettext(
                                        'Please correct the error below.',
                                        'Please correct the errors below.',
                                        errors.__len__()
                                    )
                                    return JsonResponse({'log_message': message, 'errors': errors}, status=400)
                            except RequestException:
                                transaction.savepoint_rollback(sid)
                                self.message = _('Connection error. Contact the system administrators.')
                                form.add_error('__all__', self.message)
                                errors = form.errors
                                message = ngettext(
                                    'Please correct the error below.',
                                    'Please correct the errors below.',
                                    errors.__len__()
                                )
                                return JsonResponse({'log_message': message, 'errors': errors}, status=400)

                    # si se esta agregando
                    else:
                        total_price = helpers.pay_until_top(total_price)
                        dif = amount - total_price
                        description = f'Ha realizado una reservación de {menu.schedule.name.lower()} con fecha' \
                                      f' {menu.format_date}.'
                        try:
                            transaction_json = GRAPHQL_SERV.create_transaction(
                                action='diners_reservation_reservation_create',
                                amount=float(total_price),
                                description=description,
                                person=id,
                                type='DB',
                                user=user
                            )
                            resp_json = transaction_json.json()
                            # si se efectuo correctamente la transaccion
                            if transaction_json.ok and 'errors' not in resp_json:
                                self.__transaction_id = resp_json['data']['createTransaction']['transaction']['id']
                                self.success, self.message = helpers.success_message(dif)
                                self.__balance = dif
                            else:
                                transaction.savepoint_rollback(sid)
                                self.message = resp_json['errors'][0]['message']
                                form.add_error('__all__', self.message)
                                errors = form.errors
                                message = ngettext(
                                    'Please correct the error below.',
                                    'Please correct the errors below.',
                                    errors.__len__()
                                )
                                return JsonResponse({'log_message': message, 'errors': errors}, status=400)
                        except RequestException:
                            transaction.savepoint_rollback(sid)
                            self.message = _('Connection error. Contact the system administrators.')
                            form.add_error('__all__', self.message)
                            errors = form.errors
                            message = ngettext(
                                'Please correct the error below.',
                                'Please correct the errors below.',
                                errors.__len__()
                            )
                            return JsonResponse({'log_message': message, 'errors': errors}, status=400)

            # ----------------------------------------------------------------------------
            transaction.savepoint_commit(sid)
            if self.__transaction_id:
                p = Operation(id=self.__transaction_id, reservation=object)
                p.save()

            str_list = object.__str__().split()
            str_list[2] = self.__temp_person_name
            obj_str = ' '.join(str_list)

            opts = object._meta
            data = {}

            if self.message and self.success:
                data.update(
                    pay_message=self.message,
                    success_class=self.success,
                    amount=self.__balance,
                )

            if self.operation:
                data.update(operation=self.operation)

            # si se esta modificando
            if self.object_id:
                opts = self.model._meta
                msg_dict = {
                    'name': opts.verbose_name,
                    'obj': format_html('<a href="{}">{}</a>', urlquote(self.request.path), obj_str),
                }
                msg = format_html(
                    _('The “{obj}” was changed successfully.'),
                    **msg_dict
                )
            # si se esta agregando
            else:
                obj_url = reverse(
                    'admin:%s_%s_change' % (opts.app_label, opts.model_name),
                    args=(quote(object.pk),),
                    current_app=self.request.current_app,
                )

                # Add a link to the object's change form if the user can edit the obj.

                # if admin.has_change_permission(self.request, object):
                if self.request.user.has_perm('reservation.change_reservation'):
                    obj_repr = format_html('<a href="{}">{}</a>', urlquote(obj_url), obj_str)
                else:
                    obj_repr = obj_str

                msg_dict = {
                    'name': opts.verbose_name,
                    'obj': obj_repr,
                }

                msg = format_html(
                    _('The “{obj}” was added successfully. You may add another reservation below.'),
                    **msg_dict
                )
            data.update(
                log_message=msg,
                extra_data=','.join(
                    [self.__temp_person_name, self.__pay_method, str(self.__balance), self.__position], ),
            )
            return JsonResponse(data, status=200)

    def form_invalid(self, form):
        response = super().form_invalid(form)
        if self.request.accepts('text/html'):
            return response
        else:
            errors = form.errors
            message = ngettext(
                'Please correct the error below.',
                'Please correct the errors below.',
                errors.__len__()
            )
            return JsonResponse({'log_message': message, 'errors': errors}, status=400)


class PersonAutocompleteView(autocomplete.Select2ListView):
    def get_list(self):
        person_list = cache.get('all-person')
        if self.request.user:
            user = self.request.user
            if user.person:
                area = self.forwarded.get('area', None)
                if area:
                    if self.request.user.has_perm('reservation.all_add_reservation') or \
                            self.request.user.has_perm('reservation.all_change_reservation'):
                        person_list = GRAPHQL_SERV.diners_to_area_choices(area)
                    elif self.request.user.has_perm('reservation.area_add_reservation') or \
                            self.request.user.has_perm('reservation.area_change_reservation'):
                        person_list = GRAPHQL_SERV.diners_advanced_to_person_area_choices(user.person)[0]
        return person_list


class AreaAutocompleteView(autocomplete.Select2ListView):
    def get_list(self):
        area_list = cache.get('all-area')
        if self.request.user:
            user = self.request.user
            if user.person and not user.is_superuser and user.has_perm('reservation.area_add_reservation'):
                area_list = GRAPHQL_SERV.area_to_choices_by_person(user.person)
        return area_list


class DiningRoomAutocompleteView(autocomplete.Select2ListView):
    def get_list(self):
        return GRAPHQL_SERV.diningrooms_to_choices()


class ProcessPersonView(View):
    def get(self, request, *args, **kwargs):
        return HttpResponseForbidden()

    def post(self, request, *args, **kwargs):
        try:
            result = json.loads(request.body)
            id = int(result['id'])
            resp = GRAPHQL_SERV.get_diner_api(id)
            if resp and resp.ok:
                resp_json = resp.json()
                if 'errors' in resp_json:
                    if resp_json['data']:
                        message = resp_json['data']['dinerById']['person']['name'] + ': ' + \
                                  resp_json['errors'][0]['message']
                    else:
                        message = resp_json['errors'][0]['message']
                    error = {'class_alert': 'error', 'log_message': message, 'extra_data': ''}
                    return JsonResponse(error, status=400)
                else:
                    diner = resp_json['data']['dinerById']
                    if diner:
                        class_alert, msg = helpers.message_payment(diner)
                        person = diner['person']

                        area = person['area']
                        advancepayment = person['advancepaymentRelated']
                        data = {
                            'id': area['id'],
                            'text': area['name'],
                            'is_diet': diner['isDiet'],
                            'extra_data': ','.join([
                                person['name'],
                                diner['paymentMethod'],
                                advancepayment['balance'] if advancepayment else '',
                                person['position'] or '',
                            ]),
                            'class_alert': class_alert,
                            'log_message': msg
                        }
                        return JsonResponse(data, status=200)
                    else:
                        error = {'class_alert': 'error', 'log_message': _('The diner does not exists.'),
                                 'extra_data': ''}
                        return JsonResponse(error, status=400)
            else:
                error = {'class_alert': 'error',
                         'log_message': _('Connection error. Contact the system administrators.'), 'extra_data': ''}
                return JsonResponse(error, status=400)
        except RequestException:
            error = {'class_alert': 'error', 'log_message': _('Connection error. Contact the system administrators.'),
                     'extra_data': ''}
            return JsonResponse(error, status=400)


class DetailReservationView(View):
    def get(self, request, *args, **kwargs):
        return HttpResponseBadRequest('Request should be from POST method')

    def post(self, request, *args, **kwargs):
        obj = Reservation.objects.get(id=json.loads(request.body)['id'])

        data = {'fields': {
            str(obj.__class__._meta.get_field('person').verbose_name).capitalize(): obj.person,
            str(obj.__class__._meta.get_field('menu').verbose_name).capitalize(): str(obj.menu),
            str(obj.__class__.dishes_as_html.fget.short_description).capitalize(): obj.dishes_as_html,
            str(obj.__class__.payment_dishes.fget.short_description).capitalize(): obj.payment_dishes,
            str(obj.__class__._meta.get_field('reserv_log_user').verbose_name
                ).capitalize(): obj.reserv_log_user if obj.reserv_log_user else _('Empty'),
            str(obj.__class__._meta.get_field('confirm_log_user').verbose_name
                ).capitalize(): obj.confirm_log_user if obj.confirm_log_user else _('Empty'),
            str(obj.__class__._meta.get_field('person_donate').verbose_name
                ).capitalize(): obj.person_donate if obj.person_donate else _('Empty'),
            str(obj.__class__._meta.get_field('offplan_data').verbose_name
                ).capitalize(): "".join(
                ['<span class="{}">{}</span>'.format(k, v) for k, v in obj.offplan_data.items()]
            ) if obj.offplan_data else _('Empty'),
        }
        }

        return JsonResponse(data, status=200)


class ProcessDishesView(View):
    def get(self, request, *args, **kwargs):
        return HttpResponseBadRequest('Request should be from POST method')

    def post(self, request, *args, **kwargs):
        json_resp = json.loads(request.body)
        menu_id, diet = json_resp['id'], json_resp['is_diet']
        menu = Menu.objects.get(id=menu_id) if menu_id else None
        dishes = (menu.diet_dishes.all() if diet else menu.dishes.all()) if menu else []
        return render(request, 'reservation/dish_dropdown_list_options.html', {'dishes': dishes})


class ActionFormViewMixin(FormView):
    template_name = 'reservation/actions_template.html'

    def get(self, request, *args, **kwargs):
        return HttpResponseBadRequest('Request should be from POST method')

    def post(self, request, *args, **kwargs):
        if not request.POST.get('post'):
            cache.set('all-person', GRAPHQL_SERV.diners_to_choices(), None)
            context = self.get_context_data()
            id = request.POST['id_reserv']
            context['queryset'] = Reservation.objects.filter(id=id)
            try:
                if self.validate_reserv(request, context):
                    self.context_conditions(context)
                    return self.render_to_response(context)
                return redirect('admin:reservation_reservation_sinc-list-reservs')
            except RequestException:
                messages.error(request, _('Connection error. Contact the system administrators.'))
                return redirect('admin:reservation_reservation_sinc-list-reservs')
        else:
            return super().post(request, *args, **kwargs)

    def context_conditions(self, context):
        context['form'].fields['person'].widget.attrs.update({
            'data-maximum-selection-length': context['queryset'].count()
        })

    def get_form(self, form_class=None):
        if not self.request.POST.get('post'):
            return self.get_form_class()()
        return super().get_form(form_class=form_class)

    def get_form_kwargs(self):
        form = super().get_form_kwargs()
        form['request'] = self.request
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['api_url'] = config('API_URL')
        return context

    def form_invalid(self, form):
        errors = form.errors
        message = ngettext(
            'Please correct the error below.',
            'Please correct the errors below.',
            errors.__len__()
        )
        return JsonResponse({'log_message': message, 'errors': errors}, status=400)

    def validate_reserv(self, request, context):
        is_validate = False
        queryset = context['queryset']

        condition = self.get_filter_condition()

        reserv_today = queryset.filter(condition)
        if reserv_today.count() > 0:
            context['queryset'] = reserv_today
            reserv_today_dif = queryset.exclude(condition)
            dif_count = reserv_today_dif.count()
            if dif_count > 0:
                msg_error = ngettext(
                    '<strong>A reservation</strong> cannot confirm out of plan.',
                    '<strong>%(count)s reservations</strong> cannot confirm out of plan.',
                    dif_count
                ) % {'count': dif_count}
                messages.error(request, format_html(msg_error))
            # today
            today_count = reserv_today.count()
            msg_info = ngettext(
                '<strong>The reservation</strong> to confirm is %(name)s. Select a diner below.',
                'The <strong>%(count)s reservations</strong> to confirm are %(name)s. Select %(count)s diners below.',
                today_count
            ) % {
                           'count': today_count,
                           'name': helpers.reservation_plufify(reserv_today),
                       }
            messages.info(request, format_html(msg_info))
            is_validate = True
        else:
            for elem in queryset:
                if self.invite_validation(elem):
                    if not elem.is_confirmed:
                        if self.in_time_validation(elem):
                            pass
                        else:
                            messages.error(request, format_html(self.get_message_error_intime_condition(elem)))
                    else:
                        messages.error(request, format_html(self.get_message_error_confirmed_condition(elem)))
                else:
                    messages.error(request, format_html(self.get_message_error_invite_condition(elem)))

        return is_validate

    def get_filter_condition(self):
        pass

    def get_message_error_invite_condition(self, elem):
        pass

    def get_message_error_confirmed_condition(self, elem):
        name = elem.reservation_category.name if not elem.person else \
            GRAPHQL_SERV.get_diner_api(elem.person).json()['data']['dinerById']['person']['name']
        return _('<strong>{0}</strong> reservation are confirmed.').format(name)

    def get_message_error_intime_condition(self, elem):
        pass

    def in_time_validation(self, elem):
        datetime_now = datetime.now()
        return elem.menu.date == datetime_now.date() and elem.menu.schedule.start_time <= datetime_now.time() < elem.menu.schedule.offplan_time

    def invite_validation(self, elem):
        pass


class OffPlanInviteFormView(ActionFormViewMixin):
    form_class = InviteOffPlanForm

    def get_filter_condition(self):
        datetime_now = datetime.now()
        time_now = datetime_now.time()
        is_reserv_in_time = Q(menu__date=datetime_now) & Q(menu__schedule__start_time__lte=time_now) & Q(
            menu__schedule__offplan_time__gt=time_now)
        is_reserv_not_confirmed = Q(is_confirmed=False)
        is_invite_list = Q(reservation_category__name='Invitado')

        return is_reserv_in_time & is_reserv_not_confirmed & is_invite_list

    def get_message_error_invite_condition(self, elem):
        name = elem.reservation_category.name if not elem.person else \
            GRAPHQL_SERV.get_diner_api(elem.person).json()['data']['dinerById']['person']['name']
        return _('<strong>{0}</strong> reservation are not invited.').format(name)

    def get_message_error_intime_condition(self, elem):
        name = elem.reservation_category.name if not elem.person else \
            GRAPHQL_SERV.get_diner_api(elem.person).json()['data']['dinerById']['person']['name']
        return _('<strong>{0}</strong> reservation are offtime for today ({1} - {2}).').format(
            name,
            elem.menu.schedule.start_time.strftime('%I:%M %p'),
            elem.menu.schedule.offplan_time.strftime('%I:%M %p')
        )

    def form_valid(self, form):
        ubication = form.cleaned_data['ubication']
        area = form.cleaned_data['area']
        persons = form.cleaned_data['person']

        reserv_confirmed = Reservation.objects.filter(pk__in=form.data.getlist('_selected_action'))

        if ubication == '2':
            for r in reserv_confirmed:
                r.is_confirmed = True
                r.confirm_log_user = str(self.request.user)
                r.offplan_data = {'offplan_area': area}
                r.modify_log_user.add(User.objects.create(user_id=self.request.user.id))
                r.save()
        else:
            # codificado de esta forma para que guarde los cambios en registros extendidos
            for (r, p) in zip(reserv_confirmed, persons):
                r.is_confirmed = True
                r.confirm_log_user = str(self.request.user)
                r.offplan_data = {'offplan_person': p['id']}
                if 'id_transaction' in p:
                    p = Operation(id=p['id_transaction'], reservation=r)
                    p.save()
                r.modify_log_user.add(User.objects.create(user_id=self.request.user.id))
                r.save()

        log_message = ngettext(
            '<strong>The reservation</strong> is confirmed successfuly.',
            '<strong>%(count)s reservations</strong> are confirmed successfuly.',
            reserv_confirmed.count()
        ) % {'count': reserv_confirmed.count()}

        messages.info(self.request, format_html(log_message))

        for person in persons:
            if person['payment_method'] == 'AP':
                message = _(
                    'Reservation of <strong>{0}</strong> confirmed: The diner has a balance of: <strong>${1}</strong>.'
                ).format(person['name'], person['to_pay'])
            else:
                message = _(
                    'Reservation of <strong>{0}</strong> confirmed: You must mark <strong>${1}</strong> on card.'
                ).format(person['name'], person['to_pay'])
            messages.info(self.request, format_html(message))

        return JsonResponse({'path': reverse('admin:reservation_reservation_sinc-list-reservs')}, status=200)

    def in_time_validation(self, elem):
        datetime_now = datetime.now()
        return elem.menu.date == datetime_now.date() and elem.menu.schedule.start_time <= datetime_now.time() < elem.menu.schedule.offplan_time

    def invite_validation(self, elem):
        return elem.reservation_category.name == 'Invitado'


class DonateFormView(ActionFormViewMixin):
    form_class = DonateForm

    def get_filter_condition(self):
        datetime_now = datetime.now()
        time_now = datetime_now.time()
        is_reserv_in_time = Q(menu__date=datetime_now) & Q(menu__schedule__start_time__lte=time_now) & Q(
            menu__schedule__end_time__gt=time_now)
        is_reserv_not_confirmed = Q(is_confirmed=False)
        is_not_invite_list = Q(reservation_category__name='Particular')

        return is_reserv_in_time & is_reserv_not_confirmed & is_not_invite_list

    def get_message_error_invite_condition(self, elem):
        name = elem.reservation_category.name if not elem.person else \
            GRAPHQL_SERV.get_diner_api(elem.person).json()['data']['dinerById']['person']['name']
        return _('<strong>{0}</strong> reservation are not particular.').format(name)

    def get_message_error_intime_condition(self, elem):
        name = elem.reservation_category.name if not elem.person else \
            GRAPHQL_SERV.get_diner_api(elem.person).json()['data']['dinerById']['person']['name']
        return _('<strong>{0}</strong> reservation are offtime for today ({1} - {2}).').format(
            name,
            elem.menu.schedule.start_time.strftime('%I:%M %p'),
            elem.menu.schedule.end_time.strftime('%I:%M %p')
        )

    def context_conditions(self, context):
        super().context_conditions(context)
        if context['queryset'].count() == 1:
            del context['form'].fields['person']
            context['form'].fields['count'].choices = [(1, _('one').capitalize())]
            context['form'].fields['count'].initial = 1

    def form_valid(self, form):
        person_unique = form.cleaned_data['person_unique']
        persons = form.cleaned_data['person']
        count = form.cleaned_data['count']
        reserv_confirmed = Reservation.objects.filter(pk__in=form.data.getlist('_selected_action'))

        if count == '1':
            for r in reserv_confirmed:
                r.is_confirmed = True
                r.confirm_log_user = str(self.request.user)
                r.person_donate = person_unique[0]
                r.modify_log_user.add(User.objects.create(user_id=self.request.user.id))
                r.save()

        else:
            # codificado de esta forma para que guarde los cambios en registros extendidos
            for (r, p) in zip(reserv_confirmed, persons):
                r.is_confirmed = True
                r.confirm_log_user = str(self.request.user)
                r.person_donate = p
                r.modify_log_user.add(User.objects.create(user_id=self.request.user.id))
                r.save()

        log_message = ngettext(
            '<strong>The reservation</strong> is confirmed successfuly.',
            '<strong>%(count)s reservations</strong> are confirmed successfuly.',
            reserv_confirmed.count()
        ) % {'count': reserv_confirmed.count()}

        messages.info(self.request, format_html(log_message))

        return JsonResponse({'path': reverse('admin:reservation_reservation_sinc-list-reservs')}, status=200)

    def in_time_validation(self, elem):
        datetime_now = datetime.now()
        return elem.menu.date == datetime_now.date() and elem.menu.schedule.start_time <= datetime_now.time() < elem.menu.schedule.end_time

    def invite_validation(self, elem):
        return elem.reservation_category.name == 'Particular'


class OffPlanFormView(ActionFormViewMixin):
    form_class = OffPlanForm

    def get_filter_condition(self):
        datetime_now = datetime.now()
        time_now = datetime_now.time()
        is_reserv_in_time = Q(menu__date=datetime_now) & Q(menu__schedule__end_time__lte=time_now) & Q(
            menu__schedule__offplan_time__gt=time_now)
        is_reserv_not_confirmed = Q(is_confirmed=False)
        is_not_invite_list = Q(reservation_category__name='Particular')

        return is_reserv_in_time & is_reserv_not_confirmed & is_not_invite_list

    def get_message_error_invite_condition(self, elem):
        name = elem.reservation_category.name if not elem.person else \
            GRAPHQL_SERV.get_diner_api(elem.person).json()['data']['dinerById']['person']['name']
        return _('<strong>{0}</strong> reservation are not particular.').format(name)

    def get_message_error_intime_condition(self, elem):
        name = elem.reservation_category.name if not elem.person else \
            GRAPHQL_SERV.get_diner_api(elem.person).json()['data']['dinerById']['person']['name']
        return _('<strong>{0}</strong> reservation are offtime for today ({1} - {2}).').format(
            name,
            elem.menu.schedule.end_time.strftime('%I:%M %p'),
            elem.menu.schedule.offplan_time.strftime('%I:%M %p')
        )

    def form_valid(self, form):
        ubication = form.cleaned_data['ubication']
        area = form.cleaned_data['area']
        persons = form.cleaned_data['person']

        reserv_confirmed = Reservation.objects.filter(pk__in=form.data.getlist('_selected_action'))

        if ubication == '2':
            for r in reserv_confirmed:
                r.is_confirmed = True
                r.confirm_log_user = str(self.request.user)
                r.offplan_data = {'offplan_area': area}
                r.modify_log_user.add(User.objects.create(user_id=self.request.user.id))
                r.save()
        else:
            # codificado de esta forma para que guarde los cambios en registros extendidos
            for (r, p) in zip(reserv_confirmed, persons):
                r.is_confirmed = True
                r.confirm_log_user = str(self.request.user)
                r.offplan_data = {'offplan_person': p}
                r.modify_log_user.add(User.objects.create(user_id=self.request.user.id))
                r.save()

        log_message = ngettext(
            '<strong>The reservation</strong> is confirmed successfuly.',
            '<strong>%(count)s reservations</strong> are confirmed successfuly.',
            reserv_confirmed.count()
        ) % {'count': reserv_confirmed.count()}

        messages.info(self.request, format_html(log_message))

        return JsonResponse({'path': reverse('admin:reservation_reservation_sinc-list-reservs')}, status=200)

    def in_time_validation(self, elem):
        datetime_now = datetime.now()
        return elem.menu.date == datetime_now.date() and elem.menu.schedule.end_time <= datetime_now.time() < elem.menu.schedule.offplan_time

    def invite_validation(self, elem):
        return elem.reservation_category.name == 'Particular'


class ConfirmPersonView(View):
    def get(self, request, *args, **kwargs):
        return HttpResponseBadRequest('Request should be from POST method')

    def post(self, request, *args, **kwargs):
        if request.user.has_perm('reservation.confirm_change_reservation'):
            result = json.loads(request.body)["data"]
            try:
                id = int(result['id'])
                name = result['name']
                diner_active = result['dinerRelated']['isActive']
                paymentMethod = result['dinerRelated']['paymentMethod']
                balance = Decimal(result['advancepaymentRelated']['balance'])
            except:
                return HttpResponseBadRequest('Metodo de entrada incorrecto: id, nombre, método de pago y balance.')

            error_msg = ""
            reservs = Reservation.objects.filter(person__exact=id).filter(menu__date=datetime.now())
            if diner_active:
                if reservs.count() != 0:
                    schedules = MealSchedule.objects.all()
                    verifi_reserv_day = False
                    for sched in schedules:
                        if sched.start_time <= datetime.now().time() < sched.end_time:
                            reserv_sched = reservs.filter(menu__schedule=sched.id)
                            if reserv_sched.count() != 0:
                                verifi_reserv_day = True
                                for reserv in reserv_sched:
                                    if not reserv.is_confirmed:
                                        try:
                                            reserv.is_confirmed = True
                                            reserv.confirm_log_user = str(self.request.user)
                                            reserv.save()
                                        except Error as er:
                                            error_msg = er
                                        if reserv.is_confirmed:
                                            dishes_and_price = []
                                            for resr in reserv.dishes.all():
                                                dishes_and_price.append({"dish": resr.name,
                                                                         "price": resr.price})
                                            resp = [{"type": "success",
                                                     "mess": "La reservación de %(name)s fue confirmada." % {
                                                         'name': name},
                                                     "name": name,
                                                     "date": "%s - %s" % (reserv.menu.schedule.name, str(
                                                         reserv.menu.date.strftime("%d/%m/%y"))),
                                                     "dishes": dishes_and_price,
                                                     "reserv": reserv.id}]
                                            if paymentMethod == "AP":
                                                class_alert, msg = reservation_message(name, balance)
                                                resp.append({"type": class_alert, "mess": msg, "balance": balance})
                                            return JsonResponse({"list": resp}, status=200)
                                    else:
                                        error_msg = _(
                                            "%(sched)s de %(name)s está confirmada." % {'name': name,
                                                                                        'sched': sched.name})
                            else:
                                error_msg = _("%(name)s no tiene reserva de %(sched)s para hoy." % {'name': name,
                                                                                                    'sched': sched.name})
                    if not verifi_reserv_day:
                        error_msg = "%(name)s no puede confirmar fuera de horario." % {'name': name}
                else:
                    error_msg = "%(name)s no tiene reserva para hoy." % {'name': name}
            else:
                error_msg = "%(name)s no es un comensal." % {'name': name}
        else:
            error_msg = _("You do not have permission to confirm reservations.")
        return JsonResponse(
            {"list": [{"type": "error", "mess": error_msg}]}, status=200)


class ConfirmReservView(View):
    def get(self, request, *args, **kwargs):
        return HttpResponseBadRequest('Request should be from POST method')

    def post(self, request, *args, **kwargs):
        if request.user.has_perm('reservation.confirm_change_reservation'):
            result = json.loads(request.body)
            try:
                id = int(result['id'])
            except:
                return JsonResponse(
                    {'error': "Valores incorrectos en la petición POST. Contacte al administrador del Sistema."},
                    status=500)
            error_msg = ""
            try:
                reserv = Reservation.objects.get(pk=id)
            except:
                error_msg = "La reservación no existe."
            else:
                if reserv.person != None:
                    try:
                        resp_api = GRAPHQL_SERV.get_namePerson_and_amount_by_idPerson(reserv.person).json()["data"][
                            "personById"]
                    except:
                        return JsonResponse({
                            'error': "Problema con la conexión con el Sistema de Identidad. Contacte al administrador del Sistema."},
                            status=500)
                    name = resp_api["name"]
                    paymentMethod = resp_api["dinerRelated"]["paymentMethod"]
                    if paymentMethod == "AP":
                        if resp_api["advancepaymentRelated"]:
                            balance = resp_api["advancepaymentRelated"]["balance"]
                        else:
                            balance = 0
                else:
                    name = reserv.reservation_category.name
                    paymentMethod = ""
                changue_confirm = False
                # if True:
                if confirm_start_time(reserv.menu) <= datetime.now() < confirm_end_time(reserv.menu):

                    if not reserv.is_confirmed:
                        try:
                            reserv.is_confirmed = True
                            reserv.confirm_log_user = str(self.request.user)
                            reserv.save()
                            changue_confirm = True
                            action_text = _("confirmed")
                        except Error as er:
                            error_msg = er
                    else:
                        try:
                            reserv.is_confirmed = False
                            reserv.confirm_log_user = ''
                            reserv.save()
                            changue_confirm = True
                            action_text = _("deconfirmed")
                        except Error as er:
                            error_msg = er

                if changue_confirm:
                    dishes_and_price = []
                    for resr in reserv.dishes.all():
                        dishes_and_price.append({"dish": resr.name,
                                                 "price": resr.price})
                    resp = {"type": "success",
                            "name": name,
                            "action_text": action_text,
                            "mess": _("%s's reservation was %s") % (name, action_text),
                            "date": "%s - %s" % (reserv.menu.schedule.name, str(
                                reserv.menu.date.strftime("%d/%m/%y"))),
                            "dishes": dishes_and_price,
                            "reserv": reserv.id}
                    if paymentMethod == "AP":
                        class_alert, msg = reservation_message(name, Decimal(balance))
                        resp["person"] = {"type": class_alert, "mess": msg, "balance": balance, "name": name,
                                          "dishes": dishes_and_price}
                    return JsonResponse(resp, status=200)
                else:
                    error_msg = "%(name)s no puede confirmar fuera de horario." % {'name': name}
        else:
            error_msg = _("You do not have permission to confirm reservations.")
        return JsonResponse({"type": "error", "mess": error_msg}, status=200)


class MenuDatesAvailableView(View):
    def post(self, request, *args, **kwargs):
        return HttpResponseBadRequest('Request should be from GET method')

    def get(self, request, *args, **kwargs):
        menus = Menu.objects.filter(date__gte=get_difference_day())
        dates, response = [], []
        for menu in menus:
            dates.append(menu.date)
        dates = list(set(dates))
        dates.sort(reverse=True)
        for date in dates:
            response.append({"date": date, "text": formats.date_format(date, format='l j \d\e F \d\e Y')})
        return JsonResponse({"list": response}, status=200)


class ReservCategoryView(View):
    def get(self, request, *args, **kwargs):
        return HttpResponseForbidden()

    def post(self, request, *args, **kwargs):
        data = {}
        date = json.loads(request.body)['date']
        menus = Menu.objects.filter(date=date).order_by('schedule__id')
        menu = menus.first()

        diner_close = helpers.report_time(menu)
        difference = helpers.get_difference_day()

        if difference >= diner_close:
            data['message'] = {
                'errornote': [_('You can no longer reserve for %(date)s.') % {
                    'date': formats.date_format(menu.date, format='l j \d\e F \d\e Y')
                }]
            }

            status = 400
        else:
            warnings = {}
            for category in ReservationCategory.objects.filter(meal_schedules__isnull=False).distinct():
                if category.is_active:
                    for msc in category.reservcatschedule_set.all():
                        if msc.is_active:
                            # si existe el mealschedule de categoria en el schedule del menu
                            menu = menus.filter(schedule=msc.mealschedule).first()
                            if menu:
                                m_id = Reservation.objects.filter(
                                    menu__date=date,
                                    person__isnull=True,
                                    reservation_category=category,
                                    menu__schedule=msc.mealschedule
                                )
                                m_id_count = m_id.count()
                                if m_id_count < msc.count_diners:
                                    dif = msc.count_diners - m_id_count
                                    for i in range(dif):
                                        reservation = Reservation(
                                            reservation_category=category,
                                            menu=menu,
                                            reserv_log_user=str(request.user)
                                        )
                                        reservation.save()
                                        reservation.modify_log_user.add(User.objects.create(user_id=request.user.id))
                                        reservation.dishes.set(menu.dishes.all())
                                elif m_id_count > msc.count_diners:
                                    dif = m_id_count - msc.count_diners
                                    for i in range(dif):
                                        m_id.first().delete()
                            else:
                                sched_list = warnings.get(msc.mealschedule.name) or []
                                sched_list.append(msc.reservation_category.name)
                                warnings[msc.mealschedule.name] = sched_list
                        else:
                            Reservation.objects.filter(
                                menu__date=date,
                                person__isnull=True,
                                reservation_category=category,
                                menu__schedule=msc.mealschedule
                            ).delete()
                else:
                    Reservation.objects.filter(
                        menu__date=date,
                        person__isnull=True,
                        reservation_category=category,
                    ).delete()
            if warnings:
                warnings_messages_list = []
                for key in warnings:
                    warnings_messages_list.append('%(mealschedule)s: %(categories)s' % {
                        'mealschedule': key.capitalize(),
                        'categories': ', '.join([elem for elem in warnings[key]])
                    })
                data['message'] = {
                    'successnote': [_('The followings categories grouped by mealschedules are not reserved.')],
                    'warningnote': warnings_messages_list,
                }
            else:
                data['message'] = {
                    'successnote': [_('All reservations are generated successfully.')]
                }
            status = 200

        return JsonResponse(data, status=status)


class ListReservView(View):
    def get(self, request, *args, **kwargs):
        return HttpResponseForbidden()

    def post(self, request, *args, **kwargs):
        result = json.loads(request.body)
        try:
            page = int(result['page'])
            filt_confirm = result['confirmed']
            filt_shedule = result['shedule']
            filt_diningroom = result["dinningroom"]
            filt_search = result["search"]
            filt_date_gte = result["date_gte"]
            filt_date_lte = result["date_lte"]
        except:
            return JsonResponse(
                {'error': "Valores incorrectos en la petición POST. Contacte al administrador del Sistema."},
                status=500)
        limit = settings.CANT_TUPLE_TO_SHOW
        all_reservs = getQuerySetReservation(request)
        if all_reservs != None:
            get = ""
            if filt_confirm != None:
                get = "is_confirmed=" + str(filt_confirm)
            if filt_shedule != None:
                if get != "":
                    get += "&"
                get += "menu=" + str(filt_shedule)
            if filt_diningroom != None:
                if get != "":
                    get += "&"
                get += "diningroom=" + str(filt_diningroom)
            if filt_search != None:
                if get != "":
                    get += "&"
                get += "q=" + str(filt_search)
            if filt_date_gte != None:
                if get != "":
                    get += "&"
                get += "date__gte=" + str(filt_date_gte)
            if filt_date_lte != None:
                if get != "":
                    get += "&"
                get += "date__lte=" + str(filt_date_lte)
            if get != "":
                QD = QueryDict(get)
                filt_result = ReservationFilter(QD, all_reservs)
                all_reservs = filt_result.qs
            paginator = Paginator(all_reservs, limit)
            page_obj = paginator.get_page(page)
            total = paginator.count
            total_pages = paginator.num_pages
            response = []
            # ------- PARA OBTENER LA LISTA DE PERSONAS Y COMEDORES SIN QUE SE REPITAN -------
            set_person = set()
            # set_dinning_room = set()
            for reserv in page_obj.object_list:
                if reserv.person:
                    set_person.add(reserv.person)
                # else:
                #     set_dinning_room.add(reserv.reservation_category.dining_room)
            if len(set_person) > 0:
                str_variable = "["
                for id_x in set_person:
                    str_variable = str_variable + str(id_x) + ","
                str_variable = str_variable[:-1] + "]"
                resp_api = GRAPHQL_SERV.get_general(
                    "query {personByIds(ids: " + str_variable + ") {id,name,area{name},dinerRelated {diningRoom {name}}}}",
                    None, True)
                if resp_api:
                    persons_json = resp_api.json()["data"]["personByIds"]
                else:
                    return JsonResponse({'error': 'No se puede conectar a la api'}, status=400)
            # ------------------------------------------------------------------------------
            resp_api = GRAPHQL_SERV.get_diningrooms_api()
            if resp_api:
                diningrooms_json = resp_api.json()["data"]["allDiningRooms"]
            else:
                return JsonResponse({'error': 'No se puede conectar a la api'}, status=400)

            for reserv in page_obj.object_list:
                is_confirmed = isConfirmedHtmlList(request, reserv.is_confirmed, reserv.pk)
                moreAction = moreActionReservationHtml(request, reserv.pk)
                if reserv.person:
                    person = None
                    for elem in persons_json:
                        if person == None and elem["id"] == str(reserv.person):
                            person = elem
                    if person == None:
                        person = {"name": "Comensal Desactivado", "area": {"name": "-"},
                                  "dinerRelated": {"diningRoom": {"name": "-"}}}
                    # --- PROBANDO LOS NOMBRES INDIVIDUALMENTE -------------------------------------
                    # resp_api = GRAPHQL_SERV.get_personname_areaname_dinningroomname(reserv.person)
                    # if resp_api:
                    #     person = resp_api.json()["data"]["personById"]
                    # else:
                    #     return JsonResponse({'error': 'No se puede conectar a la api'}, status=400)
                    # -----------------------------------------------------------------------------
                    response.append({
                        "id_rserv": reserv.pk,
                        "person": person["name"],
                        "diningroom": person["dinerRelated"]["diningRoom"]["name"],
                        "area": person["area"]["name"],
                        "menu": str(reserv.menu),
                        "is_confirmed": is_confirmed,
                        "more_action": moreAction,
                    })
                else:
                    diningroom = None
                    for elem in diningrooms_json:
                        if diningroom == None and elem["id"] == str(reserv.reservation_category.dining_room):
                            diningroom = elem
                    response.append({
                        "id_rserv": reserv.pk,
                        "person": reserv.reservation_category.name,
                        "diningroom": diningroom["name"],
                        "area": "-",
                        "menu": str(reserv.menu),
                        "is_confirmed": is_confirmed,
                        "more_action": moreAction,
                    })
            if len(getActionsReservations(request)) > 0:
                action = True
            else:
                action = False
            return JsonResponse({'reservs': response, 'total': total, 'pages': total_pages, "action": action},
                                status=200)
        else:
            return JsonResponse({'error': 'No se puede conectar a la api'}, status=400)


class DiningRoomNameView(View):
    def get(self, request, *args, **kwargs):
        return HttpResponseForbidden()

    def post(self, request, *args, **kwargs):
        result = json.loads(request.body)
        id = int(result['id'])
        resp_api = GRAPHQL_SERV.get_nameDiningroom_by_idDiningroom_api_honly(id)
        if resp_api:
            resp_api_json = resp_api.json()["data"]["diningRoomById"]["name"]
            response = {"dinningrooms": resp_api_json}
            return JsonResponse(response, status=resp_api.status_code)
        else:
            return JsonResponse({'error': 'No se puede conectar a la api'}, status=400)


class DeleteReservView(View):
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        if request.user.has_perm('reservation.delete_reservation'):
            result = json.loads(request.body)
            try:
                id_reserv = int(result['id'])
            except:
                return JsonResponse(
                    {'error': "Valores incorrectos en la petición POST. Contacte al administrador del Sistema."},
                    status=500)
            try:
                reserv = Reservation.objects.get(pk=id_reserv)
            except:
                error_msg = _("The reservation does not exist.")
            else:
                person = reserv.person
                if person != None:
                    try:
                        person_api = GRAPHQL_SERV.get_diner_api(person)
                        diner = person_api.json()['data']['dinerById']
                        name = diner['person']['name']
                        pay = diner['paymentMethod']
                        position = diner['person']['position']
                    except:
                        return JsonResponse({
                            'error': "Problema con la conexión con el Sistema de Identidad. Contacte al administrador del Sistema."},
                            status=500)
                else:
                    name = reserv.reservation_category.name
                text = 'La "Reservación de %s para %s" fue eliminada con éxito.' % (name, str(reserv.menu))
                response = {"type": "success", "mess": text}
                if person:
                    if validate_pay(pay, reserv.menu.schedule, reserv.menu.date.isoweekday(), position):
                        sid = transaction.savepoint()
                        try:
                            amount = pay_until_top(sum([d.price for d in reserv.dishes.all()]))
                            date_m = "%s para la fecha %s" % (
                                reserv.menu.schedule.name.lower(), reserv.menu.format_date)
                            reserv.delete()
                            trans = GRAPHQL_SERV.create_transaction(
                                action='diners_reservation_reservation_delete',
                                amount=float(amount),
                                description='Se eliminó la reservación de %s' % date_m,
                                person=person,
                                type='CR',
                                user=request.user.username
                            ).json()['data']['createTransaction']['transaction']
                            success, message = reservation_message(name, float(trans['resultingBalance']))
                            response["person"] = {"type": success, "mess": message}
                            transaction.savepoint_commit(sid)
                        except:
                            transaction.savepoint_rollback(sid)
                            return JsonResponse({
                                'error': "Problema con la conexión con el Sistema de Identidad. Contacte al administrador del Sistema."},
                                status=500)
                    else:
                        reserv.delete()
                else:
                    reserv.delete()
                return JsonResponse(response, status=200)
        else:
            error_msg = _("You do not have permission to delete reservations.")
        return JsonResponse({"type": "error", "mess": error_msg}, status=200)

    def get(self, request, *args, **kwargs):
        if request.user.has_perm('reservation.delete_reservation'):
            try:
                id_reserv = int(request.GET["reserv"])
            except:
                return JsonResponse(
                    {'error': "Valores incorrectos en la petición GET. Contacte al administrador del Sistema."},
                    status=500)
            try:
                reserv = Reservation.objects.get(pk=id_reserv)
            except:
                error_msg = _("The reservation does not exist.")
            else:
                menu = reserv.menu
                difference = get_difference_day()
                diner_close = report_time(menu)
                amount = None
                if difference >= diner_close:
                    error_msg = _('The reservation cannot delete')
                else:
                    if reserv.person != None:
                        try:
                            person_api = GRAPHQL_SERV.get_diner_api(reserv.person)
                            diner = person_api.json()['data']['dinerById']
                            name = diner['person']['name']
                            pay = diner['paymentMethod']
                            position = diner['person']['position']
                        except:
                            return JsonResponse({
                                'error': "Problema con la conexión con el Sistema de Identidad. Contacte al administrador del Sistema."},
                                status=500)
                        if validate_pay(pay, reserv.menu.schedule, reserv.menu.date.isoweekday(), position):
                            amount = pay_until_top(sum([d.price for d in reserv.dishes.all()]))
                    else:
                        name = reserv.reservation_category.name
                    reserv_text = "Reservación de %s para %s." % (name, str(reserv.menu))
                    pre_text = '¿Está seguro de que quiere borrar la "'
                    suf_text = '"?'
                    if amount != None:
                        suf_text += " Se reintegrará $" + str(amount) + "."
                    return JsonResponse(
                        {"type": "success", "reserv_text": reserv_text, "pre_text": pre_text, "suf_text": suf_text,
                         "id_reserv": id_reserv},
                        status=200)
        else:
            error_msg = _("You do not have permission to delete reservations.")
        return JsonResponse({"type": "error", "mess": error_msg}, status=200)


class ActionView(View):
    def get(self, request, *args, **kwargs):
        try:
            ids = request.GET["ids"]
            action = request.GET["action"]
        except:
            return JsonResponse(
                {'error': "Valores incorrectos en la petición GET. Contacte al administrador del Sistema."},
                status=500)
        ids = ids.split(",")
        response, status = getattr(self, action, None)(request, ids)
        return JsonResponse(response, status=status)

    def post(self, request, *args, **kwargs):
        result = json.loads(request.body)
        try:
            action = result['action']
            ids = result['ids']
        except:
            return JsonResponse(
                {'error': "Valores incorrectos en la petición POST. Contacte al administrador del Sistema."},
                status=500)
        response, status = getattr(self, action, None)(request, ids)
        return JsonResponse(response, status=status)

    def deleteReservations(self, request, ids):
        status = 200
        if request.user.has_perm('reservation.all_delete_reservation'):
            if request.method == 'GET':
                change_list = []
                ids_reserv = []
                no_change_list = []
                for id_reserv in ids:
                    try:
                        reserv = Reservation.objects.get(pk=id_reserv)
                    except:
                        no_change_list.append(_("The reservation %s does not exist." % id_reserv))
                    else:
                        menu = reserv.menu
                        difference = get_difference_day()
                        diner_close = report_time(menu)
                        amount = None
                        if reserv.person != None:
                            try:
                                person_api = GRAPHQL_SERV.get_diner_api(reserv.person)
                                diner = person_api.json()['data']['dinerById']
                                name = diner['person']['name']
                                pay = diner['paymentMethod']
                                position = diner['person']['position']
                            except:
                                status = 500
                                return {
                                    'error': "Problema con la conexión con el Sistema de Identidad. Contacte al administrador del Sistema."}, status
                            if validate_pay(pay, reserv.menu.schedule, reserv.menu.date.isoweekday(), position):
                                amount = pay_until_top(sum([d.price for d in reserv.dishes.all()]))
                        else:
                            name = reserv.reservation_category.name
                        if difference >= diner_close:
                            no_change_list.append(
                                'Reservación de %s para %s ha expirado el período válido para ser borrada.' % (
                                    name, str(reserv.menu)))
                        else:
                            reserv_text = "Reservación de %s para %s." % (name, str(reserv.menu))
                            if amount != None:
                                reserv_text += " Se reintegrará $" + str(amount) + "."
                            change_list.append(reserv_text)
                            ids_reserv.append(id_reserv)
                body_html = ""
                if len(no_change_list) != 0:
                    body_html += "<h2>ERROR:</h2><ul>"
                    for elem in no_change_list:
                        body_html += "<li>" + elem + "</li>"
                    body_html = body_html + "</ul>"
                if len(change_list) != 0:
                    body_html += "<h2>Reservaciones que serán borradas:</h2><ul>"
                    for elem in change_list:
                        body_html += "<li>" + elem + "</li>"
                    body_html = body_html + "</ul>"
                    text_head = "¿Está seguro?"
                    func_yes = "executeAction(["
                    for elem in ids_reserv:
                        func_yes += elem + ","
                    func_yes = func_yes[:-1] + "])"
                    modal = {"type": "yesornot", "func": {"yes": func_yes}}
                else:
                    text_head = "No seleccionó reservaciones que se puedan borrar"
                    modal = {"type": "ok"}

                return {"type": "success", "text_head": text_head, "body_html": body_html,
                        "modal": modal}, status
            else:
                list_mess = []
                for id_reserv in ids:
                    try:
                        reserv = Reservation.objects.get(pk=id_reserv)
                    except:
                        list_mess.append({"type": "error", "mess": _("The reservation does not exist.")})
                    else:
                        person = reserv.person
                        if person != None:
                            try:
                                person_api = GRAPHQL_SERV.get_diner_api(person)
                                diner = person_api.json()['data']['dinerById']
                                name = diner['person']['name']
                                pay = diner['paymentMethod']
                                position = diner['person']['position']
                            except:
                                status = 500
                                return {
                                    'error': "Problema con la conexión con el Sistema de Identidad. Contacte al administrador del Sistema."}, status
                        else:
                            name = reserv.reservation_category.name
                        text = 'La "Reservación de %s para %s" fue eliminada con éxito.' % (name, str(reserv.menu))
                        list_mess.append({"type": "success", "mess": text})
                        if person:
                            if validate_pay(pay, reserv.menu.schedule, reserv.menu.date.isoweekday(), position):
                                sid = transaction.savepoint()
                                try:
                                    amount = pay_until_top(sum([d.price for d in reserv.dishes.all()]))
                                    date_m = "%s para la fecha %s" % (
                                        reserv.menu.schedule.name.lower(), reserv.menu.format_date)
                                    reserv.delete()
                                    trans = GRAPHQL_SERV.create_transaction(
                                        action='diners_reservation_reservation_delete',
                                        amount=float(amount),
                                        description='Se eliminó la reservación de %s' % date_m,
                                        person=person,
                                        type='CR',
                                        user=request.user.username
                                    ).json()['data']['createTransaction']['transaction']
                                    success, message = reservation_message(name, float(trans['resultingBalance']))
                                    list_mess.append({"type": success, "mess": message})
                                    transaction.savepoint_commit(sid)
                                except:
                                    transaction.savepoint_rollback(sid)
                                    status = 500
                                    return {
                                        'error': "Problema con la conexión con el Sistema de Identidad. Contacte al administrador del Sistema."}, status
                            else:
                                reserv.delete()
                        else:
                            reserv.delete()
                return {"lis": list_mess}, status
        else:
            error_msg = _("You do not have permission to delete reservations.")
        return {"type": "error", "mess": error_msg}, status


class APIView(View):
    def get(self, request, *args, **kwargs):
        return HttpResponseForbidden()

    def post(self, request, *args, **kwargs):
        result = json.loads(request.body)
        try:
            query = result['query']
            token = bool(result['token'])
        except:
            return JsonResponse(
                {'error': "Valores incorrectos en la petición POST. Contacte al administrador del Sistema."},
                status=500)
        variables = result['variables'] or None
        try:
            response = GRAPHQL_SERV.get_general(query=query, variables=variables, token=token).json()
        except:
            return JsonResponse(
                {'error': _("Error connecting to Identity API. Contact the System administrator.")},
                status=500)
        return JsonResponse(response, status=200)
