import datetime
import json
import operator
from datetime import datetime
from decimal import Decimal
from functools import reduce

from decouple import config
from django.conf import settings
from django.contrib import admin
from django.contrib import messages
from django.contrib.admin import helpers
from django.contrib.admin.exceptions import DisallowedModelAdminToField
from django.contrib.admin.options import IncorrectLookupParameters
from django.contrib.admin.templatetags.admin_urls import add_preserved_filters
from django.contrib.admin.utils import (
    NestedObjects, model_ngettext, quote, unquote, lookup_spawns_duplicates,
)
from django.core.cache import cache
from django.core.exceptions import (
    FieldDoesNotExist, PermissionDenied, ValidationError,
)
from django.core.exceptions import (ObjectDoesNotExist, )
from django.db import models, router, transaction
from django.db.models import Q, Count
from django.db.models.constants import LOOKUP_SEP
from django.forms import BaseInlineFormSet
from django.http import HttpResponseBadRequest, HttpResponseRedirect
from django.template.response import SimpleTemplateResponse, TemplateResponse
from django.urls import NoReverseMatch, path, reverse_lazy, reverse
from django.utils.formats import date_format
from django.utils.html import format_html
from django.utils.text import capfirst
from django.utils.translation import gettext as _, ngettext, gettext_lazy as _
from import_export.admin import ImportExportModelAdmin, ImportExportActionModelAdmin
from requests.exceptions import RequestException

from diners.utils.helpers import get_difference_day, confirm_end_time, confirm_start_time, validate_pay, \
    success_message, reservation_message, \
    report_time, context_action, pay_until_top
from .forms import DateReportForm, ReservationCategoryAdminForm, ReservationForm
from .models import DishCategory, Dish, MealSchedule, Menu, Reservation, User, ReservationCategory, ReservCatSchedule, \
    Operation
from .resources import ReservationResource, DishCategoryResource, DishResource, MenuResource
from .utils import getActionsReservations
from .views import ProcessPersonView, AreaAutocompleteView, PersonAutocompleteView, \
    DiningRoomAutocompleteView, DetailReservationView, \
    ConfirmPersonView, MenuDatesAvailableView, ReservCategoryView, ReservationView, ProcessDishesView, ListReservView, \
    DiningRoomNameView, ConfirmReservView, DeleteReservView, ActionView, APIView, OffPlanInviteFormView, DonateFormView, \
    OffPlanFormView

IS_POPUP_VAR = '_popup'
TO_FIELD_VAR = '_to_field'
GRAPHQL_SERV = settings.GRAPHQL_SERVICE


@transaction.atomic
def delete_selected(modeladmin, request, queryset):
    opts = modeladmin.model._meta
    app_label = opts.app_label
    deletable_objects, model_count, perms_needed, protected = modeladmin.get_deleted_objects(queryset, request)
    if request.POST.get('post') and not protected:
        if perms_needed:
            raise PermissionDenied
        n = queryset.count()
        if n:
            for obj in queryset:
                obj_display = str(obj)
                modeladmin.log_deletion(request, obj, obj_display)

            data = []
            sid = transaction.savepoint()
            try:
                # convertir queryset en json, metodo para hacer una copia
                for element in queryset:
                    person = element.person
                    amount = sum([d.price for d in element.dishes.all()])
                    date_m = "%s para la fecha %s" % (element.menu.schedule.name.lower(), element.menu.format_date)
                    weekday = element.menu.date.isoweekday()
                    if person:
                        try:
                            aux = GRAPHQL_SERV.get_PM_position_by_idPerson(person).json()["data"]["personById"]
                            py_m = aux["dinerRelated"]["paymentMethod"]
                            position = aux["position"]
                        except RequestException:
                            modeladmin.message_user(request, _('Connection error. Contact the system administrators.'),
                                                    messages.ERROR)
                            return HttpResponseRedirect('/')

                        if validate_pay(py_m, element.menu.schedule, weekday, position):
                            data.append({"person": person, "name": aux['name'], "amount": amount, "date_m": date_m})
                modeladmin.delete_queryset(request, queryset)
                for elem in data:
                    trans = GRAPHQL_SERV.create_transaction(
                        action='diners_reservation_reservation_delete',
                        amount=pay_until_top(float(elem['amount'])),
                        description='Se eliminó la reservación de %s' % elem['date_m'],
                        person=elem['person'],
                        type='CR',
                        user=request.user.username
                    ).json()['data']['createTransaction']['transaction']

                    success, message = reservation_message(elem['name'],
                                                           float(trans['resultingBalance']))
                    modeladmin.message_user(request, format_html(message), success)
                modeladmin.message_user(request, _("Successfully deleted %(count)d %(items)s.") % {
                    "count": n, "items": model_ngettext(modeladmin.opts, n)
                }, messages.SUCCESS)
                transaction.savepoint_commit(sid)
            except Exception:
                modeladmin.message_user(request, _('Connection error. Contact the system administrators.'),
                                        messages.ERROR)
                transaction.savepoint_rollback(sid)

        # Return None to display the change list page again.
        return None
    objects_name = model_ngettext(queryset)

    if perms_needed or protected:
        title = _("Cannot delete %(name)s") % {"name": objects_name}
    else:
        title = _("Are you sure?")

    context = {
        **modeladmin.admin_site.each_context(request),
        'title': title,
        'objects_name': str(objects_name),
        'deletable_objects': [deletable_objects],
        'model_count': dict(model_count).items(),
        'queryset': queryset,
        'perms_lacking': perms_needed,
        'protected': protected,
        'opts': opts,
        'action_checkbox_name': helpers.ACTION_CHECKBOX_NAME,
        'media': modeladmin.media,
        'api_url': config('API_URL'),
    }

    request.current_app = modeladmin.admin_site.name

    # Display the confirmation page
    return TemplateResponse(request, modeladmin.delete_selected_confirmation_template or [
        "admin/%s/%s/delete_selected_confirmation.html" % (app_label, opts.model_name),
        "admin/%s/delete_selected_confirmation.html" % app_label,
        "admin/delete_selected_confirmation.html"
    ], context)


def confirm_invite_reserv_off_plan(modeladmin, request, queryset):
    title = _('off plan invites confirmation').capitalize()
    value_form = 'invite_off_plan_form'
    value_action = 'confirm_invite_reserv_off_plan'

    context = context_action(modeladmin, queryset, request, title, value_form, value_action)

    return OffPlanInviteFormView.as_view(extra_context=context)(request)


def confirm_donate(modeladmin, request, queryset):
    title = _('donate confirmation').capitalize()
    value_form = 'donate_form'
    value_action = 'confirm_donate'

    context = context_action(modeladmin, queryset, request, title, value_form, value_action)

    return DonateFormView.as_view(extra_context=context)(request)


def confirm_normal_reserv_off_plan(modeladmin, request, queryset):
    title = _('off plan confirmation').capitalize()
    value_form = 'off_plan_form'
    value_action = 'confirm_normal_reserv_off_plan'

    context = context_action(modeladmin, queryset, request, title, value_form, value_action)

    return OffPlanFormView.as_view(extra_context=context)(request)


delete_selected.short_description = _('Delete selected objects')
confirm_invite_reserv_off_plan.short_description = _('Confirm reservations of invites off plan')
confirm_donate.short_description = _('Confirm reservations as donate')
confirm_normal_reserv_off_plan.short_description = _('Confirm reservations off plan')


@admin.register(DishCategory)
class DishCategoryAdmin(ImportExportModelAdmin):
    resources_class = DishCategoryResource
    list_display = ('name', 'option_number', 'creation_date', 'modification_date')


@admin.register(Dish)
class DishAdmin(ImportExportModelAdmin):
    resources_class = DishResource
    list_per_page = 30
    list_display = ('name', 'dish_category', 'price', 'creation_date', 'modification_date')
    list_filter = ['dish_category', 'price']
    search_fields = ['name']


@admin.register(MealSchedule)
class MealScheduleAdmin(admin.ModelAdmin):
    list_display = ('name', 'get_start_time', 'get_end_time', 'get_offplan_time', 'get_report_time', 'is_payment')

    def get_start_time(self, obj):
        return obj.start_time.strftime('%I:%M %p')

    get_start_time.short_description = _('start time')

    def get_end_time(self, obj):
        return obj.end_time.strftime('%I:%M %p')

    get_end_time.short_description = _('end time')

    def get_offplan_time(self, obj):
        return obj.offplan_time.strftime('%I:%M %p')

    get_offplan_time.short_description = _('offplan time')

    def get_report_time(self, obj):
        return obj.report_time.strftime('%I:%M %p')

    get_report_time.short_description = _('report time')


@admin.register(Menu)
class MenuAdmin(ImportExportActionModelAdmin):
    resources_class = MenuResource
    fields = ['schedule', 'date', 'dishes', 'diet_dishes']
    filter_horizontal = ('dishes', 'diet_dishes')
    list_per_page = 30
    list_display = (
        'date',
        'schedule',
        'dishes_as_html',
        'payment_dishes',
        'dishes_as_html_diet',
        'payment_dishes_diet'
    )
    list_filter = ['date']
    search_fields = ['date', 'dishes__name']


class ReservCatScheduleFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        # si se esta modificando
        if self.instance.pk:
            value_list = [form.cleaned_data for form in self.forms if form.cleaned_data]
            value_to_delete_list = [elem for elem in value_list if 'DELETE' in elem and elem['DELETE']]
            # compara si los elementos que se van a eliminar son todos los que existen
            if value_to_delete_list == value_list:
                raise ValidationError('Debe tener al menos un horario de comida')


class ReservationCategoryMealscheduleInline(admin.TabularInline):
    model = ReservCatSchedule
    formset = ReservCatScheduleFormSet
    fields = ('mealschedule', 'reservation_category', 'count_diners', 'is_active')
    extra = 1


def confirm_bulk(modeladmin, request, queryset):
    cat_no_confirmed = queryset.filter(is_confirmable=False)
    cat_confirmed = queryset.filter(is_confirmable=True)
    cat_no_resv = []
    for reserv_categ in cat_confirmed:
        reserv_queryset = Reservation.objects.filter(reservation_category=reserv_categ, menu__date=datetime.now())
        if reserv_queryset.count() > 0:
            for reserv in reserv_queryset:
                reserv.is_confirmed = True
                reserv.save()
        else:
            cat_no_resv.append(reserv_categ)
            cat_confirmed = cat_confirmed.exclude(pk=reserv_categ.pk)
    if cat_no_confirmed:
        error_msg = 'No se pueden confirmar masivamente las reservas de las siguientes categorías: %s.' % (
            ', '.join(['<strong>%s</strong>' % elem_no_confirm.name for elem_no_confirm in cat_no_confirmed])
        )
        modeladmin.message_user(request, format_html(error_msg), messages.ERROR)
    if cat_no_resv:
        error_msg = 'No existen reservas en las siguientes categorías: %s para este horario.' % (
            ', '.join(['<strong>%s</strong>' % elem_no_resv.name for elem_no_resv in cat_no_resv])
        )
        modeladmin.message_user(request, format_html(error_msg), messages.ERROR)
    if cat_confirmed:
        success_msg = 'Se confirmaron masivamente las reservas de las siguientes categorías: %s.' % (
            ', '.join(['<strong>%s</strong>' % elem_confirm.name for elem_confirm in cat_confirmed])
        )
        modeladmin.message_user(request, format_html(success_msg), messages.SUCCESS)


confirm_bulk.short_description = 'Confirmar masivo.'


@admin.register(ReservationCategory)
class ReservationCategoryAdmin(admin.ModelAdmin):
    form = ReservationCategoryAdminForm
    inlines = (ReservationCategoryMealscheduleInline,)
    list_display = ('name', 'dining_room', 'get_schedules_count', 'is_confirmable', 'is_active')
    list_editable = ('is_active',)
    actions = [confirm_bulk]

    def has_delete_permission(self, request, obj=None):
        return False

    def get_actions(self, request):
        actions = super().get_actions(request)
        if not request.user.has_perm('reservation.confirm_change_reservation'):
            del actions['confirm_bulk']
        return actions

    def get_urls(self):
        urls = super().get_urls()
        _urls = [
            path('generate-reserv-categ/', self.admin_site.admin_view(ReservCategoryView.as_view()),
                 name='%s_%s_generate_reserv_categ' % self.get_model_info()),
            path('menu-dates-available/', self.admin_site.admin_view(MenuDatesAvailableView.as_view()),
                 name='%s_%s_menu_dates_available' % self.get_model_info()),
        ]
        return _urls + urls

    def get_model_info(self):
        app_label = self.model._meta.app_label
        model_name = self.model._meta.model_name
        return app_label, model_name

    def get_schedules_count(self, obj):
        text_html = _('Empty')
        if obj.reservcatschedule_set.all():
            text_html = '<br>'.join(
                '%s %s (<strong>%s</strong>) ' % (
                    '<img src="/static/admin/img/icon-%s.svg" alt="%s">' % (
                        'yes' if elem.is_active else 'no', elem.is_active
                    ),
                    elem.mealschedule.name, elem.count_diners
                ) for elem in obj.reservcatschedule_set.all()
            )
        return format_html(text_html)

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['api_url'] = config('API_URL')
        return super().changelist_view(request, extra_context=extra_context)

    get_schedules_count.short_description = _('schedule (count)')

    class Media:
        js = ('js/cookie.js', 'js/jquery.modal.min.js', 'js/api_conection.js', 'js/category.js')
        css = {'all': ('css/jquery.modal.min.css', 'css/form_mobile.css', 'css/loader.css')}


class DiningRoomPersonFilter(admin.SimpleListFilter):
    model_admin = None
    title = _('dining rooms')
    parameter_name = 'dining_room'

    def lookups(self, request, model_admin):
        all_dining_rooms = []
        try:
            dining_rooms = cache.get('all-dinning-rooms').json()
            res_dining_rooms = dining_rooms['data']['allDiningRooms']
            for element in res_dining_rooms:
                all_dining_rooms.append((element['id'], element['name']))
        except RequestException:
            pass

        return all_dining_rooms

    def queryset(self, request, queryset):
        diningroom_id = self.value()
        if diningroom_id:
            try:
                dining_rooms = cache.get('dinning-rooms-ids')
                if not dining_rooms or dining_rooms['id'] != diningroom_id:
                    diner_set = GRAPHQL_SERV.get_diners_by_dinningroom(diningroom_id).json()['data']['diningRoomById'][
                        'dinerSet']
                    cache.set('dinning-rooms-ids', {'id': diningroom_id, 'dinerset': diner_set}, None)
                queryset_aux = queryset.filter(
                    person__in=[list_id['person']['id'] for list_id in cache.get('dinning-rooms-ids')['dinerset']])

                cat = ReservationCategory.objects.filter(dining_room=diningroom_id)
                queryset = queryset_aux | queryset.filter(reservation_category__in=cat)
            except RequestException:
                self.model_admin.message_user(request, _('Connection error. Contact the system administrators.'),
                                              messages.ERROR)
                return HttpResponseRedirect('/')

        return queryset


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    form = ReservationForm
    list_per_page = 20
    list_display = (
        'get_person_model',
        'get_diningroom_model',
        'get_area_person_model',
        'menu',
        'is_confirmed'
    )
    date_hierarchy = 'menu__date'
    search_fields = ['reservation_category__name']
    list_filter = [
        'menu__date',
        'is_confirmed',
        ('menu__schedule', admin.RelatedOnlyFieldListFilter)
    ]
    list_editable = ('is_confirmed',)
    actions = [delete_selected, confirm_invite_reserv_off_plan, confirm_donate, confirm_normal_reserv_off_plan]

    def get_urls(self):
        urls = super().get_urls()
        _urls = [
            path('report/', self.admin_site.admin_view(self.report_view),
                 name='%s_%s_report' % self.get_model_info()),
            path('camera_qr/', self.admin_site.admin_view(self.camera_view),
                 name='%s_%s_camera_qr' % self.get_model_info()),
            path('areacomplete/', self.admin_site.admin_view(AreaAutocompleteView.as_view()),
                 name='%s_%s_areacomplete' % self.get_model_info()),
            path('personcomplete/', self.admin_site.admin_view(PersonAutocompleteView.as_view()),
                 name='%s_%s_personcomplete' % self.get_model_info()),
            path('diningroomcomplete/', self.admin_site.admin_view(DiningRoomAutocompleteView.as_view()),
                 name='%s_%s_dinningroomcomplete' % self.get_model_info()),
            path('process-person/', self.admin_site.admin_view(ProcessPersonView.as_view()),
                 name='%s_%s_processperson' % self.get_model_info()),
            path('confirm_person/', self.admin_site.admin_view(ConfirmPersonView.as_view()),
                 name='%s_%s_confirm_person' % self.get_model_info()),
            path('detail-reservation/', self.admin_site.admin_view(DetailReservationView.as_view()),
                 name='%s_%s_detail_reservation' % self.get_model_info()),
            path('process-dishes/', self.admin_site.admin_view(ProcessDishesView.as_view()),
                 name='%s_%s_process_dishes' % self.get_model_info()),
            path('reservs_return/', self.admin_site.admin_view(ListReservView.as_view()),
                 name='%s_%s_reservs_return' % self.get_model_info()),
            path('diningroom_name/', self.admin_site.admin_view(DiningRoomNameView.as_view()),
                 name='%s_%s_diningroom_name' % self.get_model_info()),
            path('confirm_reservation/', self.admin_site.admin_view(ConfirmReservView.as_view()),
                 name='%s_%s_confirm_reservation' % self.get_model_info()),
            path('delete_reservation/', self.admin_site.admin_view(DeleteReservView.as_view()),
                 name='%s_%s_delete_reservation' % self.get_model_info()),
            path('action_reserv/', self.admin_site.admin_view(ActionView.as_view()),
                 name='%s_%s_action_reserv' % self.get_model_info()),
            path('api_identity/', self.admin_site.admin_view(APIView.as_view()),
                 name='%s_%s_api_identity' % self.get_model_info()),
            path('invite_offplan/', self.admin_site.admin_view(self.invite_offplan_view),
                 name='%s_%s_invite_offplan' % self.get_model_info()),
            path('donate/', self.admin_site.admin_view(self.donate_view),
                 name='%s_%s_donate' % self.get_model_info()),
            path('offplan/', self.admin_site.admin_view(self.offplan_view),
                 name='%s_%s_offplan' % self.get_model_info()),
            path('', self.admin_site.admin_view(self.sinc_list_reservs_view),
                 name='%s_%s_sinc-list-reservs' % self.get_model_info()),
        ]
        return _urls + urls

    def get_list_editable(self, request):
        list_editable = ()
        if not request.user.has_perm('reservation.confirm_change_reservation'):
            for elem in self.list_editable:
                if not elem.__eq__('is_confirmed'):
                    list_editable = (
                        *list_editable,
                        elem,
                    )
            self.list_editable = list_editable
        elif 'is_confirmed' not in self.list_editable:
            self.list_editable = (
                *self.list_editable,
                'is_confirmed',
            )

    def get_changelist_instance(self, request):
        self.get_list_editable(request)
        return super().get_changelist_instance(request)

    def get_list_filter(self, request):
        list_filter = super().get_list_filter(request)
        diningroom_filter = DiningRoomPersonFilter
        diningroom_filter.model_admin = self
        list_filter = (
            *list_filter,
            diningroom_filter
        )
        return list_filter

    def get_actions(self, request):
        actions = super().get_actions(request)
        if not self.has_delete_permission(request):
            if 'delete_selected' in actions:
                del actions['delete_selected']
        if not request.user.has_perm("%s.%s" % (self.get_model_info()[0], "confirm_change_reservation")):
            if 'confirm_invite_reserv_off_plan' in actions:
                del actions['confirm_invite_reserv_off_plan']
            if 'confirm_donate' in actions:
                del actions['confirm_donate']
            if 'confirm_normal_reserv_off_plan' in actions:
                del actions['confirm_normal_reserv_off_plan']
        return actions

    def get_list_display(self, request):
        list_display = super().get_list_display(request)

        def more_actions(obj):
            preserved_filter = self.get_preserved_filters(request)
            full_html = ''
            if self.has_delete_permission(request):
                cancel_url = reverse('admin:%s_%s_delete' % (self.get_model_info()), args=(obj.id,))
                cancel_url += '?' + preserved_filter if preserved_filter else ''
                full_html += '''<a title="{}" class="padding-action" href="{}">
                                    <img src="{}img/trash-o.png" width="20">
                                </a>'''.format(_('Cancel'), cancel_url, settings.STATIC_URL)
            full_html += '''<button title="{}" class="info-button padding-action" data-id="{}">
                                <img src="{}img/info-circle.png" width="20">
                            </button>'''.format(_('Info'), obj.id, settings.STATIC_URL)
            return format_html(full_html)

        more_actions.short_description = _('Actions')

        list_display = (
            *list_display,
            more_actions,
        )
        return list_display

    def get_deleted_objects(self, objs, request):
        """
            Find all objects related to ``objs`` that should also be deleted. ``objs``
            must be a homogeneous iterable of objects (e.g. a QuerySet).

            Return a nested list of strings suitable for display in the
            template with the ``unordered_list`` filter.
            """
        admin_site = self.admin_site
        try:
            obj = objs[0]
        except IndexError:
            return [], {}, set(), []
        else:
            using = router.db_for_write(obj._meta.model)
        collector = NestedObjects(using=using)
        collector.collect(objs)
        perms_needed = set()

        def format_callback(obj):
            model = obj.__class__
            has_admin = model in admin_site._registry
            opts = obj._meta

            if isinstance(obj, Reservation):
                no_edit_link = '%s' % obj
            else:
                no_edit_link = '%s' % getattr(obj, obj._meta.fields[-1].name)

            if has_admin:
                if not admin_site._registry[model].has_delete_permission(request, obj):
                    perms_needed.add(opts.verbose_name)
                try:
                    admin_url = reverse('%s:%s_%s_change'
                                        % (admin_site.name,
                                           opts.app_label,
                                           opts.model_name),
                                        None, (quote(obj.pk),))
                except NoReverseMatch:
                    # Change url doesn't exist -- don't display link to edit
                    return no_edit_link

                # Display a link to the admin page.
                return format_html('{}: <a href="{}">{}</a>',
                                   capfirst(opts.verbose_name),
                                   admin_url,
                                   obj)
            else:
                # Don't display link to edit, because it either has no
                # admin or is edited inline.
                return no_edit_link

        to_delete = collector.nested(format_callback)

        protected = [format_callback(obj) for obj in collector.protected]
        model_count = {model._meta.verbose_name_plural: len(objs) for model, objs in collector.model_objs.items()}

        return to_delete, model_count, perms_needed, protected

    def add_view(self, request, form_url='', extra_context=None):
        try:
            form_url = reverse('admin:%s_%s_add' % self.get_model_info())
            extra_context = extra_context or {}
            extra_context['title'] = _('Add reservation').capitalize()
            extra_context['type_view'] = 'add'
            extra_context['qr_action'] = 'select_QR_person'
            return self.changeform_view(request, form_url=form_url, extra_context=extra_context)
        except RequestException:
            self.message_user(request, _('Connection error. Contact the system administrators.'), messages.ERROR)
            return HttpResponseRedirect('/')

    def change_view(self, request, object_id, form_url='', extra_context=None):
        try:
            form_url = reverse('admin:%s_%s_change' % (self.get_model_info()), args=(object_id,))
            extra_context = extra_context or {}
            extra_context['title'] = _('Edit reservation').capitalize()
            extra_context['type_view'] = 'change'
            return self.changeform_view(request, object_id=object_id, form_url=form_url, extra_context=extra_context)
        except RequestException:
            self.message_user(request, _('Connection error. Contact the system administrators.'), messages.ERROR)
            return HttpResponseRedirect('/')
        except ObjectDoesNotExist:
            self.message_user(request, _('The reservation you are trying to access does not exist'), messages.ERROR)
            return HttpResponseRedirect(
                request.META.get('HTTP_REFERER', reverse_lazy('admin:%s_%s_changelist' % self.get_model_info())))

    def delete_view(self, request, object_id, extra_context=None):
        try:
            reservation = Reservation.objects.get(pk=object_id)
            menu = reservation.menu
            difference = get_difference_day()
            diner_close = report_time(menu)

            if reservation.person:
                resp_json = GRAPHQL_SERV.get_diner_api(reservation.person).json()

                if "errors" in resp_json:
                    text = '<strong>' + resp_json['data']['dinerById']['person']['name'] + '</strong>: ' + \
                           resp_json['errors'][0]['message']
                    self.message_user(request, format_html(text), messages.ERROR)
                    return HttpResponseRedirect(reverse_lazy('admin:%s_%s_changelist' % self.get_model_info()))
            # si pasa de las 48 horas
            if difference >= diner_close:
                self.message_user(request, _('The reservation cannot delete'), messages.ERROR)
                return HttpResponseRedirect(
                    request.META.get('HTTP_REFERER', reverse_lazy('admin:%s_%s_changelist' % self.get_model_info())))
            else:
                return super().delete_view(request, object_id, extra_context=extra_context)
        except ObjectDoesNotExist:
            self.message_user(request, _('The reservation you are trying to delete does not exist'), messages.ERROR)
            return HttpResponseRedirect(
                request.META.get('HTTP_REFERER', reverse_lazy('admin:%s_%s_changelist' % self.get_model_info())))

    def _delete_view(self, request, object_id, extra_context):
        def delete_log(name, obj, opts, request, to_field):
            str_list = obj.__str__().split()
            str_list[2] = name
            obj_display = ' '.join(str_list)
            attr = str(to_field) if to_field else opts.pk.attname
            obj_id = obj.serializable_value(attr)
            self.log_deletion(request, obj, obj_display)
            self.delete_model(request, obj)
            return obj_display, obj_id

        opts = self.model._meta
        app_label = opts.app_label

        to_field = request.POST.get(TO_FIELD_VAR, request.GET.get(TO_FIELD_VAR))
        if to_field and not self.to_field_allowed(request, to_field):
            raise DisallowedModelAdminToField("The field %s cannot be referenced." % to_field)

        obj = self.get_object(request, unquote(object_id), to_field)

        if not self.has_delete_permission(request, obj):
            raise PermissionDenied

        if obj is None:
            return self._get_obj_does_not_exist_redirect(request, opts, object_id)

        # Populate deleted_objects, a data structure of all related objects that
        # will also be deleted.
        deleted_objects, model_count, perms_needed, protected = self.get_deleted_objects([obj], request)

        if request.POST and not protected:  # The user has confirmed the deletion.
            if perms_needed:
                raise PermissionDenied

            person = obj.person

            if person:
                person_api = GRAPHQL_SERV.get_diner_api(person)
                diner = person_api.json()['data']['dinerById']
                name = diner['person']['name']
                pay = diner['paymentMethod']
                position = diner['person']['position']

                if validate_pay(pay, obj.menu.schedule, obj.menu.date.isoweekday(), position):
                    try:
                        amount = pay_until_top(sum([d.price for d in obj.dishes.all()]))
                        date_m = "%s para la fecha %s" % (obj.menu.schedule.name.lower(), obj.menu.format_date)

                        transaction = GRAPHQL_SERV.create_transaction(
                            action='diners_reservation_reservation_delete',
                            amount=float(amount),
                            description='Se eliminó la reservación de %s' % date_m,
                            person=person,
                            type='CR',
                            user=request.user.username
                        ).json()['data']['createTransaction']['transaction']
                    except RequestException:
                        self.message_user(request, _('Connection error. Contact the system administrators.'),
                                          messages.ERROR)
                        return HttpResponseRedirect('/')
                    else:
                        obj_display, obj_id = delete_log(name, obj, opts, request, to_field)
                        return self.response_delete_mod(request, obj_display, obj_id, transaction)
                else:
                    obj_display, obj_id = delete_log(name, obj, opts, request, to_field)
                    return self.response_delete_mod(request, obj_display, obj_id, None)
            else:
                name = obj.reservation_category.name
                obj_display, obj_id = delete_log(name, obj, opts, request, to_field)
                return self.response_delete_mod(request, obj_display, obj_id, None)

        object_name = str(opts.verbose_name)

        if perms_needed or protected:
            title = _("Cannot delete %(name)s") % {"name": object_name}
        else:
            title = _("Are you sure?")

        context = {
            **self.admin_site.each_context(request),
            'title': title,
            'object_name': object_name,
            'object': obj,
            'deleted_objects': deleted_objects,
            'model_count': dict(model_count).items(),
            'perms_lacking': perms_needed,
            'protected': protected,
            'opts': opts,
            'app_label': app_label,
            'preserved_filters': self.get_preserved_filters(request),
            'is_popup': IS_POPUP_VAR in request.POST or IS_POPUP_VAR in request.GET,
            'to_field': to_field,
            'api_url': config('API_URL'),
            **(extra_context or {}),
        }

        return self.render_delete_form(request, context)

    def response_delete_mod(self, request, obj_display, obj_id, transaction):
        """
        Determine the HttpResponse for the delete_view stage.
        """
        opts = self.model._meta

        if IS_POPUP_VAR in request.POST:
            popup_response_data = json.dumps({
                'action': 'delete',
                'value': str(obj_id),
            })
            return TemplateResponse(request, self.popup_response_template or [
                'admin/%s/%s/popup_response.html' % (opts.app_label, opts.model_name),
                'admin/%s/popup_response.html' % opts.app_label,
                'admin/popup_response.html',
            ], {
                                        'popup_response_data': popup_response_data,
                                    })

        self.message_user(
            request,
            _('The “%(obj)s” was deleted successfully.') % {
                'name': opts.verbose_name,
                'obj': obj_display,
            },
            messages.SUCCESS,
        )

        if transaction:
            success, message = success_message(float(transaction['resultingBalance']))
            self.message_user(request, format_html(message), success)

        if self.has_change_permission(request, None):
            post_url = reverse(
                'admin:%s_%s_changelist' % (opts.app_label, opts.model_name),
                current_app=self.admin_site.name,
            )
            preserved_filters = self.get_preserved_filters(request)
            post_url = add_preserved_filters(
                {'preserved_filters': preserved_filters, 'opts': opts}, post_url
            )
        else:
            post_url = reverse('admin:index', current_app=self.admin_site.name)
        return HttpResponseRedirect(post_url)

    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        context = dict(self.admin_site.each_context(request))
        extra_context['opts'] = self.model._meta
        extra_context['api_url'] = config('API_URL')
        extra_context['object_id'] = object_id
        extra_context['form_data_url'] = form_url

        defaults = {'extra_context': {**context, **(extra_context or {})}}
        request.current_app = self.admin_site.name
        return ReservationView.as_view(**defaults)(request)

    def changelist_view(self, request, extra_context=None):
        from django.contrib.admin.views.main import ERROR_FLAG
        opts = self.model._meta
        app_label = opts.app_label

        if request.method == 'GET' or not cache.get('all-dinning-rooms'):
            try:
                cache.set('all-dinning-rooms', GRAPHQL_SERV.get_diningrooms_api(), None)
            except RequestException:
                self.message_user(request, _('Connection error. Contact the system administrators.'), messages.ERROR)
                return HttpResponseRedirect('/')

        if not self.has_view_or_change_permission(request):
            raise PermissionDenied

        try:
            cl = self.get_changelist_instance(request)
        except IncorrectLookupParameters:
            # Se proporcionaron parámetros de búsqueda extravagantes, así que redirija a la página principal de la
            # lista de cambios, sin parámetros, y pase un parámetro 'no válido = 1 a través de la cadena de consulta.
            # Si se proporcionaron parámetros extravagantes y el parámetro 'inválido = 1' ya estaba en la cadena de
            # consulta, algo está mal con la base de datos, así que muestre una página de error.

            if ERROR_FLAG in request.GET:
                return SimpleTemplateResponse('admin/invalid_setup.html', {
                    'title': _('Database error'),
                })
            return HttpResponseRedirect(request.path + '?' + ERROR_FLAG + '=1')

        # Si la solicitud se POST(ió), esto podría ser una acción masiva o una edición masiva. Intente buscar una
        # acción o confirmación primero, pero si esta no es una acción, la POST pasará a la verificación de edición
        # masiva, a continuación.
        action_failed = False
        selected = request.POST.getlist(helpers.ACTION_CHECKBOX_NAME)

        # para que no se realizen acciones con las reservaciones ya pagadas - David Mosquera Hernandez
        valid_selected = []
        msns_critical = []
        if 'delete_selected' in request.POST.getlist('action'):
            for element in selected:
                try:
                    reserv = Reservation.objects.get(pk=element)
                    combine = report_time(reserv.menu)
                    difference = get_difference_day()
                    if reserv.person:
                        resp_json = GRAPHQL_SERV.get_namePerson_by_idPerson(reserv.person).json()
                        name_person_reserv = resp_json['data']['personById']['name']

                        if "errors" in resp_json:
                            msns_critical.append(
                                '<strong>' + name_person_reserv + '</strong>: ' + resp_json['errors'][0]['message'])
                    else:
                        name_person_reserv = reserv.reservation_category.name
                    if difference <= combine:
                        valid_selected.append(element)
                    else:
                        msns_critical.append(
                            "Ya ha expirado el período válido para eliminar la reservacion: ------ %s; %s" % (
                                name_person_reserv, reserv.menu))
                except RequestException:
                    self.message_user(request, _('Connection error. Contact the system administrators.'),
                                      messages.ERROR)
                    return HttpResponseRedirect('/')
            if len(msns_critical) > 0:
                for element in msns_critical:
                    self.message_user(request, format_html(element), messages.ERROR)
                selected = valid_selected
        # -------------------------------David Mosquera Hernandez------------------------------------

        actions = self.get_actions(request)

        # Acciones sin confirmación
        if (actions and request.method == 'POST' and
                'index' in request.POST and '_save' not in request.POST):
            if selected:
                que = cl.get_queryset(request).filter(pk__in=selected)
                response = self.response_action(request, queryset=que)
                if response:
                    return response
                else:
                    action_failed = True
            else:
                if len(msns_critical) == 0:  # para que no salga el mensaje si hay errores
                    msg = _("Items must be selected in order to perform "
                            "actions on them. No items have been changed.")
                    self.message_user(request, msg, messages.WARNING)
                action_failed = True

        # Acciones con confirmación
        if (actions and request.method == 'POST' and
                helpers.ACTION_CHECKBOX_NAME in request.POST and
                'index' not in request.POST and '_save' not in request.POST):
            if selected:
                que = cl.get_queryset(request).filter(pk__in=selected)
                response = self.response_action(request, queryset=que)
                if response:
                    return response
                else:
                    action_failed = True

        if action_failed:
            # Vuelve a la página de la lista de cambios para evitar volver a enviar el formulario si el usuario
            # actualiza el navegador o usa el botón "No, llévame de vuelta" en la página de confirmación de la acción.
            return HttpResponseRedirect(request.get_full_path())

        # If we're allowing changelist editing, we need to construct a formset
        # for the changelist given all the fields to be edited. Then we'll
        # use the formset to validate/process POSTed data.
        formset = cl.formset = None
        # Handle POSTed bulk-edit data.
        if request.method == 'POST' and cl.list_editable and '_save' in request.POST:
            if not self.has_change_permission(request):
                raise PermissionDenied

            FormSet = self.get_changelist_formset(request)
            modified_objects = self._get_list_editable_queryset(request, FormSet.get_default_prefix())
            formset = cl.formset = FormSet(request.POST, request.FILES, queryset=modified_objects)

            if formset.is_valid():
                changecount = 0
                msns_warning = []
                msns_success = []
                for form in formset.forms:
                    if form.has_changed():
                        obj = self.save_form(request, form, change=True)
                        # Cambio para los mensajes de alerta al comensal sobre la cantidad de dinero que le queda
                        if obj.person:
                            try:
                                resp_json = GRAPHQL_SERV.get_namePerson_and_amount_by_idPerson(obj.person).json()
                            except RequestException:
                                self.message_user(request,
                                                  _('Connection error. Contact the system administrators.'),
                                                  messages.ERROR)
                                return HttpResponseRedirect('/')

                            person = resp_json["data"]["personById"]
                            name = person['name']
                            if obj.is_confirmed:
                                if Reservation.objects.filter(person__exact=obj.person).filter(
                                        menu__date__gte=datetime.now()).filter(menu__schedule=1).count() < 3:
                                    if person['dinerRelated']['paymentMethod'] == 'AP':
                                        if "errors" in resp_json:
                                            success = "error"
                                            message = "<strong>" + name + "</strong>: " + \
                                                      resp_json["errors"][0][
                                                          "message"]
                                        else:
                                            amount = Decimal(person['advancepaymentRelated']['balance'])
                                            success, message = reservation_message(person['name'], amount)

                                        if success == "success":
                                            msns_success.append(message)
                                        elif success == "warning":
                                            msns_warning.append(message)
                                        else:
                                            msns_critical.append(message)
                        else:
                            name = obj.reservation_category.name

                        combine_ope = confirm_start_time(obj.menu)
                        combine_end = confirm_end_time(obj.menu)
                        difference = datetime.now()

                        if combine_ope <= difference < combine_end:
                            if obj.person_donate:
                                mss = 'No se puede modificar el confirmado a <strong>{0}</strong> con menú' \
                                      ' <strong>{1}</strong> porque fue confirmado como donativo.'.format(
                                    name, str(obj.menu)
                                )
                                msns_critical.append(mss)
                            elif obj.offplan_data:
                                mss = 'No se puede modificar el confirmado a <strong>{0}</strong> con menú' \
                                      ' <strong>{1}</strong> porque fue confirmado como fuera de plan.'.format(
                                    name, str(obj.menu)
                                )
                                msns_critical.append(mss)
                            elif obj.reservation_category.name == 'Invitado':
                                mss = 'No se puede modificar el confirmado a <strong>{0}</strong> con menú ' \
                                      '<strong>{1}</strong>. Confirme la reserva como invitado fuera de plan'.format(
                                    name, str(obj.menu)
                                )
                                msns_critical.append(mss)
                            else:
                                obj.confirm_log_user = str(request.user) if obj.is_confirmed else ''
                                self.save_model(request, obj, form, change=True)
                                obj.modify_log_user.add(User.objects.create(user_id=request.user.id))
                                self.save_related(request, form, formsets=[], change=True)
                                change_msg = self.construct_change_message(request, form, None)
                                self.log_change(request, obj, change_msg)
                                changecount += 1
                        else:
                            mss = "No se puede modificar el confirmado de la reservación por estar fuera de horario (%s - %s): ------ %s, %s" % (
                                obj.menu.schedule.start_time.strftime('%I:%M %p'),
                                obj.menu.schedule.end_time.strftime('%I:%M %p'),
                                name,
                                obj.menu)
                            self.message_user(request, mss, messages.ERROR)
                        # ----------------------------------By David Mosquera------------------------------------

                if changecount:
                    msg = ngettext(
                        "%(count)s %(name)s was changed successfully.",
                        "%(count)s %(name)s were changed successfully.",
                        changecount
                    ) % {
                              'count': changecount,
                              'name': model_ngettext(opts, changecount),
                          }
                    self.message_user(request, msg, messages.SUCCESS)
                for msn_succ in msns_success:
                    self.message_user(request, format_html(msn_succ), messages.SUCCESS)
                for msn_warn in msns_warning:
                    self.message_user(request, format_html(msn_warn), messages.WARNING)
                for msn_crit in msns_critical:
                    self.message_user(request, format_html(msn_crit), messages.ERROR)

                return HttpResponseRedirect(request.get_full_path())

        # Handle GET -- construct a formset for display.
        elif cl.list_editable and self.has_change_permission(request):
            FormSet = self.get_changelist_formset(request)
            formset = cl.formset = FormSet(queryset=cl.result_list)

        # Build the list of media to be used by the formset.
        if formset:
            media = self.media + formset.media
        else:
            media = self.media

        # Build the action form and populate it with available actions.
        if actions:
            action_form = self.action_form(auto_id=None)
            action_form.fields['action'].choices = self.get_action_choices(request)
            media += action_form.media
        else:
            action_form = None

        selection_note_all = ngettext(
            '%(total_count)s selected',
            'All %(total_count)s selected',
            cl.result_count
        )

        context = {
            **self.admin_site.each_context(request),
            'module_name': str(opts.verbose_name_plural),
            'selection_note': _('0 of %(cnt)s selected') % {'cnt': len(cl.result_list)},
            'selection_note_all': selection_note_all % {'total_count': cl.result_count},
            'title': cl.title,
            'is_popup': cl.is_popup,
            'to_field': cl.to_field,
            'cl': cl,
            'media': media,
            'has_add_permission': self.has_add_permission(request),
            'opts': cl.opts,
            'action_form': action_form,
            'actions_on_top': self.actions_on_top,
            'actions_on_bottom': self.actions_on_bottom,
            'actions_selection_counter': self.actions_selection_counter,
            'preserved_filters': self.get_preserved_filters(request),
            'api_url': config('API_URL'),
            'qr_action': "confirm_QR_person",
            **(extra_context or {}),
        }

        request.current_app = self.admin_site.name

        return TemplateResponse(request, self.change_list_template or [
            'admin/%s/%s/change_list.html' % (app_label, opts.model_name),
            'admin/%s/change_list.html' % app_label,
            'admin/change_list.html'
        ], context)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user:
            if request.user.has_perm('reservation.all_view_reservation'):
                pass
            elif request.user.has_perm('reservation.area_view_reservation'):
                try:
                    list_person = \
                        GRAPHQL_SERV.get_idsPersons_of_area_by_idPerson(request.user.person).json()['data'][
                            'personById'][
                            'area'][
                            'personSet']
                    qs = qs.filter(person__in=[list_id['id'] for list_id in list_person])
                except RequestException:
                    self.message_user(request, _('Connection error. Contact the system administrators.'),
                                      messages.ERROR)
                    return HttpResponseRedirect('/')
            else:
                qs = qs.filter(person__exact=request.user.person)
        return qs

    def get_model_info(self):
        app_label = self.model._meta.app_label
        model_name = self.model._meta.model_name
        return app_label, model_name

    def report_view(self, request):
        request.current_app = self.admin_site.name
        context = dict(self.admin_site.each_context(request))
        context['title'] = _('reservations report').capitalize()
        context['opts'] = self.model._meta
        form = DateReportForm()

        if request.method == 'POST':
            form = DateReportForm(request.POST)
            if form.is_valid():
                date_lower = form.cleaned_data['date_start']
                date_upper = form.cleaned_data['date_end']
                dining_room = form.cleaned_data['dining_room']
                try:
                    areas_api = GRAPHQL_SERV.get_idPerson_and_nameArea_by_all_areas_api().json()['data']['allAreas']
                except RequestException:
                    self.message_user(request, _('Connection error. Contact the system administrators.'),
                                      messages.ERROR)
                    return HttpResponseRedirect('/')
                menus = Menu.objects.filter(date__range=[date_lower, date_upper])
                if menus.count() > 0:
                    reports = []
                    QD = None
                    # si selecciono un comedor
                    if dining_room != '0':
                        try:
                            dining_persons = \
                                GRAPHQL_SERV.get_nameDiningroom_by_idDiningroom_api(dining_room).json()[
                                    'data']['diningRoomById']
                            # filtra las personas y las categorias de reservaciones que pertenecen al comedor
                            QD = Q(person__in=[p['person']['id'] for p in dining_persons['dinerSet']]) | Q(
                                reservation_category__dining_room=dining_room)
                            context['dining_room'] = dining_persons['name']
                        except RequestException:
                            self.message_user(request,
                                              _('Connection error. Contact the system administrators.'),
                                              messages.ERROR)
                            return HttpResponseRedirect('/')
                    end_time = MealSchedule.objects.get(id=1).report_time
                    difference = get_difference_day()
                    if date_lower == date_upper and date_lower == difference.date() and datetime.now().time() < end_time:
                        messages.warning(request, _('Wait until %(time)s.') % {'time': end_time.strftime('%I:%M %p')})
                    else:
                        for sched in MealSchedule.objects.all():
                            reservs = Reservation.objects.filter(menu__in=menus, menu__schedule=sched)
                            if reservs.count() > 0:
                                if QD:
                                    # aplica el filtro del comedor si existe
                                    reservs = reservs.filter(QD)
                                # agrupa los platos y sus cantidades a cocinar
                                dishes_count = []
                                for e in reservs.values('dishes').annotate(count=Count('dishes')).order_by('-count'):
                                    if (e['dishes'] != None):
                                        dishes_count.append(
                                            {'name': Dish.objects.get(id=e['dishes']).as_html, 'count': e['count']})
                                # agrupa los platos y sus cantidades que se confirmaron
                                dishes_count_confirmed = []
                                for e in reservs.filter(is_confirmed=True).values('dishes').annotate(count=Count('dishes')).order_by('-count'):
                                    if e['dishes'] != None:
                                        dishes_count_confirmed.append({'name': Dish.objects.get(id=e['dishes']).as_html, 'count': e['count']})
                                # cantidad de reservas por areas
                                areas_list = []
                                for x in areas_api:
                                    count = reservs.filter(person__in=[p['id'] for p in x['personSet']]).count()
                                    if count > 0:
                                        areas_list.append({'name': x['name'], 'count': count})
                                cat_query = reservs.filter(person__isnull=True).values(
                                    'reservation_category__name').annotate(
                                    count=Count('reservation_category')).order_by('-count')
                                # cantidad de reservas por categorias de reservacion
                                cat_list = [
                                    {'name': x['reservation_category__name'], 'count': x['count']} for x in cat_query
                                ]
                                # lista de los no confirmados y el totan de veces que
                                # no confirmo en el rango de fecha determinado
                                not_confirmed = []
                                # cantidad de no confirmados por cada persona
                                for x in reservs.filter(person__isnull=False, is_confirmed=False).values(
                                        'person').annotate(count=Count('person')).order_by('-count'):
                                    not_confirmed.append({'id_person': x['person'], 'count': x['count']})
                                # cantidad de no confirmados por cada categoria de reservacion
                                for x in cat_query.filter(is_confirmed=False):
                                    not_confirmed.append(
                                        {'id_person': x['reservation_category__name'], 'count': x['count']})
                                # fuera de plan de las reservas con categoria invitado
                                invites = []
                                offplan_q = ~Q(offplan_data=[])
                                for elem in reservs.filter(offplan_q, Q(reservation_category__name='Invitado')).values(
                                        'reservation_category__name', 'offplan_data').annotate(
                                    count=Count('offplan_data')).order_by('-count'):
                                    op_info = list(elem['offplan_data'].items())[0]
                                    invites.append(
                                        {
                                            'type_offplan': op_info[0],
                                            'id_offplan': op_info[1],
                                            'category': elem['reservation_category__name'],
                                            'count': elem['count']
                                        }
                                    )
                                # fuera de plan de las reservas que no son categoria invitado
                                offplan = []
                                for elem in reservs.filter(offplan_q, person__isnull=False).values(
                                        'offplan_data').annotate(count=Count('offplan_data')).order_by('-count'):
                                    op_info = list(elem['offplan_data'].items())[0]
                                    offplan.append(
                                        {
                                            'type_offplan': op_info[0],
                                            'id_offplan': op_info[1],
                                            'count': elem['count']
                                        }
                                    )
                                reports.append({
                                    'name': sched,
                                    'planning': reservs.count(),
                                    'real': reservs.filter(is_confirmed=True).count(),
                                    'dishes_count': dishes_count,
                                    'dishes_count_confirmed': dishes_count_confirmed,
                                    'areas': areas_list,
                                    'categories': cat_list,
                                    'not_confirmed': not_confirmed,
                                    'count_not_confirmed': sum(i['count'] for i in not_confirmed),
                                    'invites': invites,
                                    'count_invites': sum(i['count'] for i in invites),
                                    'offplan': offplan,
                                    'count_offplan': sum(i['count'] for i in offplan),
                                })
                        # aqui
                        summary = {"planning": 0, "real": 0, 'not_confirmed': 0}
                        for report in reports:
                            summary["planning"] = summary["planning"] + report['planning']
                            summary["real"] = summary["real"] + report["real"]
                            summary['not_confirmed'] = summary['not_confirmed'] + report['count_not_confirmed']

                        if date_lower == date_upper:
                            messages.success(request, _('Report for {0}').format(date_format(date_lower)))
                        else:
                            messages.success(request, _('Report between {0} and {1}').format(date_format(date_lower),
                                                                                             date_format(date_upper)))
                        context['summary'] = summary
                        context['reports'] = reports
                else:
                    if date_lower == date_upper:
                        messages.warning(request, _(
                            'There is still no menu for {0}.').format(date_format(date_lower)))
                    else:
                        messages.warning(request, _(
                            'There is still no menu between {0} and {1}.').format(date_format(date_lower),
                                                                                  date_format(date_upper)))
            else:
                messages.error(request, _('Sorry something went wrong, check the inputs and try again please.'))
        context['form'] = form
        context['api_url'] = config('API_URL')
        return TemplateResponse(request, 'reservation/report_template.html', context)

    def invite_offplan_view(self, request):
        opts = self.model._meta
        context = {
            **self.admin_site.each_context(request),
            'title': _('off plan invites confirmation').capitalize(),
            'opts': opts,
            'action_checkbox_name': helpers.ACTION_CHECKBOX_NAME,
            'value_form': 'invite_off_plan_form',
            'value_action': 'confirm_invite_reserv_off_plan',
            'media': self.media,
        }
        request.current_app = self.admin_site.name

        return OffPlanInviteFormView.as_view(extra_context=context)(request)

    def donate_view(self, request):
        opts = self.model._meta
        context = {
            **self.admin_site.each_context(request),
            'title': _('donate confirmation').capitalize(),
            'opts': opts,
            'action_checkbox_name': helpers.ACTION_CHECKBOX_NAME,
            'value_form': 'donate_form',
            'value_action': 'confirm_donate',
            'media': self.media,
        }
        request.current_app = self.admin_site.name

        return DonateFormView.as_view(extra_context=context)(request)

    def offplan_view(self, request):
        opts = self.model._meta
        context = {
            **self.admin_site.each_context(request),
            'title': _('off plan confirmation').capitalize(),
            'opts': opts,
            'action_checkbox_name': helpers.ACTION_CHECKBOX_NAME,
            'value_form': 'off_plan_form',
            'value_action': 'confirm_normal_reserv_off_plan',
            'media': self.media,
        }
        request.current_app = self.admin_site.name

        return OffPlanFormView.as_view(extra_context=context)(request)

    def sinc_list_reservs_view(self, request):
        request.current_app = self.admin_site.name
        context = dict(self.admin_site.each_context(request))
        context['title'] = _('sinc list reserv').capitalize()
        context['opts'] = self.model._meta
        context["actions"] = getActionsReservations(request)
        context['qr_action'] = "confirm_QR_person"
        context['list_shedules'] = [{"id": shedul.pk, "name": shedul.name} for shedul in MealSchedule.objects.all()]
        try:
            context['list_dinning_room'] = GRAPHQL_SERV.get_diningrooms_api().json()["data"]["allDiningRooms"]
        except RequestException:
            self.message_user(request,
                              _('Connection error. Contact the system administrators.'),
                              messages.ERROR)
            return HttpResponseRedirect('/')
        return TemplateResponse(request, 'reservation/sinc_list_reservs.html', context)

    def camera_view(self, request):
        request.current_app = self.admin_site.name
        context = dict(self.admin_site.each_context(request))
        context['title'] = _('Camera QR').capitalize()
        context['opts'] = self.model._meta
        context['is_popup'] = True

        if request.method == 'GET':
            return TemplateResponse(request, 'reservation/camera_qr.html', context)
        else:
            return HttpResponseBadRequest('Request should be from Get method')

    def get_person_model(self, obj):
        return obj.get_person or obj.reservation_category

    def get_area_person_model(self, obj):
        return obj.get_area

    def get_diningroom_model(self, obj):
        html_format = ('person', obj.person) if obj.person else ('dining_room', obj.reservation_category.dining_room)
        return format_html('<span class="{}">{}</span>'.format(*html_format))

    def get_resource_class(self):
        return ReservationResource

    get_person_model.short_description = _('person')
    get_area_person_model.short_description = _('area')
    get_diningroom_model.short_description = _('dining room')

    def get_search_results(self, request, queryset, search_term):
        """
        Return a tuple containing a queryset to implement the search
        and a boolean indicating if the results may contain duplicates.
        """

        # Apply keyword searches.
        def construct_search(field_name):
            if field_name.startswith('^'):
                return "%s__istartswith" % field_name[1:]
            elif field_name.startswith('='):
                return "%s__iexact" % field_name[1:]
            elif field_name.startswith('@'):
                return "%s__search" % field_name[1:]
            # Use field_name if it includes a lookup.
            opts = queryset.model._meta
            lookup_fields = field_name.split(LOOKUP_SEP)
            # Go through the fields, following all relations.
            prev_field = None
            for path_part in lookup_fields:
                if path_part == 'pk':
                    path_part = opts.pk.name
                try:
                    field = opts.get_field(path_part)
                except FieldDoesNotExist:
                    # Use valid query lookups.
                    if prev_field and prev_field.get_lookup(path_part):
                        return field_name
                else:
                    prev_field = field
                    if hasattr(field, 'get_path_info'):
                        # Update opts to follow the relation.
                        opts = field.get_path_info()[-1].to_opts
            # Otherwise, use the field with icontains.
            return "%s__icontains" % field_name

        use_distinct = False
        search_fields = self.get_search_fields(request)
        if search_fields and search_term:
            # Obtener las identidades de la API que coincidan (nombre, area) con search_term -- David Mosquera
            queryset_aux = None
            # Busqueda en la API por el nombre de la identidad
            try:
                identitys = GRAPHQL_SERV.get_person_api_by_name(search_term).json()['data']['personByName']
            except RequestException:
                self.message_user(request, _('Connection error. Contact the system administrators.'),
                                  messages.ERROR)
                return HttpResponseRedirect('/')
            for identity in identitys:
                if queryset_aux is None:
                    queryset_aux = queryset.filter(person__exact=(int(identity['id'])))
                else:
                    queryset_aux = queryset_aux | queryset.filter(person__exact=(int(identity['id'])))
            # Busqueda en la API por el area de la identidad
            try:
                identitys_area = GRAPHQL_SERV.get_area_api_by_name(search_term).json()['data']['areaByName']
            except RequestException:
                self.message_user(request, _('Connection error. Contact the system administrators.'),
                                  messages.ERROR)
                return HttpResponseRedirect('/')
            for identity in identitys_area:
                for aux in identity["personSet"]:
                    if queryset_aux is None:
                        queryset_aux = queryset.filter(person__exact=(int(aux["id"])))
                    else:
                        queryset_aux = queryset_aux | queryset.filter(person__exact=(int(aux["id"])))
            orm_lookups = [construct_search(str(search_field))
                           for search_field in search_fields]
            for bit in search_term.split():
                or_queries = [models.Q(**{orm_lookup: bit})
                              for orm_lookup in orm_lookups]
                if queryset_aux is None:
                    queryset_aux = queryset.filter(reduce(operator.or_, or_queries))
                else:
                    queryset_aux = queryset_aux | queryset.filter(reduce(operator.or_, or_queries))
            if queryset_aux is not None:
                queryset = queryset_aux
            else:
                queryset = Reservation.objects.none()
            use_distinct |= any(lookup_spawns_duplicates(self.opts, search_spec) for search_spec in orm_lookups)
        return queryset, use_distinct

    class Media:
        js = (
            'js/confirm_qr2.js',
            'js/qr2.js', 'js/cookie.js', 'js/jquery.modal.min.js', 'js/main_list.js',)
        css = {'all': ('css/jquery.modal.min.css', 'css/main_list.css')}
