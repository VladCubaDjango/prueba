from datetime import datetime, timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.admin import helpers
from django.utils.dateparse import parse_date
from django.utils.formats import get_format, date_format
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

AMOUNT_TOP = 18


def validate_pay(paymentMethod, schedule, weekday, position):
    if paymentMethod == 'AP' and schedule.is_payment and (
            (weekday != 6 and weekday != 7) or position in settings.LIST_POSITIONS_PAY_WEEKEND):
        return True
    else:
        return False


def date_from_request(request_post_date):
    post_date = parse_date(request_post_date)
    if post_date is None:
        post_date = datetime.strptime(request_post_date, get_format('DATE_INPUT_FORMATS')[0]).date()
    return post_date, date_format(post_date)


def sum_price_dishes(dishes):
    return sum([d.price for d in dishes])


def price_dishes(dishes):
    return '$%s' % sum_price_dishes(dishes)


def sorted_by_option_number(dishes):
    return [d for d in sorted(dishes, key=lambda d: d.dish_category.option_number)]


def html_dishes(dishes):
    return mark_safe('<br>'.join('%s (<strong>$%s</strong>)' % (d.name, d.price) for d in dishes))


def confirm_start_time(menu):
    return datetime.combine(menu.date, menu.schedule.start_time)


def confirm_end_time(menu):
    return datetime.combine(menu.date, menu.schedule.end_time)


def offplan_time(menu):
    return datetime.combine(menu.date, menu.schedule.offplan_time)


def report_time(menu):
    return datetime.combine(menu.date, menu.schedule.report_time)


def get_difference_day():
    today = datetime.now()
    difference = today + timedelta(days=2)
    # si es viernes
    if today.isoweekday() == 5:
        difference = today + timedelta(days=4)
    return difference


def to_money(amount):
    return Decimal(amount).quantize(Decimal('.00'))


def message_payment(diner):
    person = diner['person']
    name = person['name']
    if diner['paymentMethod'] == "AP":
        amount = to_money(person['advancepaymentRelated']['balance'])
        class_alert, msg = reservation_message(name, amount)
    else:
        class_alert = 'success'
        msg = _('The diner: <strong>{0}</strong> pays by card.').format(name)
    return class_alert, msg


def isDietText(boolean):
    if boolean:
        return _("yes").capitalize()
    else:
        return _("no").capitalize()


def typeOperationText(type):
    if type == 'CR':
        return _('credit').capitalize()
    else:
        return _('debit').capitalize()


def formatDateOperations(date):
    return datetime.strptime(date, '%Y-%m-%dT%H:%M:%S.%f')


def pager_personal(page, size):
    res = []
    if size > 10:
        sum = 0
        rest = 0
        res.append(1)
        rest = page - 4
        if rest <= 1:
            rest = rest - 2
            sum = rest * -1
            rest = 2
        sum = sum + (page + 3)
        if sum >= size:
            rest = rest - (sum - size + 1)
            sum = size - 1
        count = rest
        while count <= sum:
            res.append(count)
            count = count + 1
        res.append(size)
    else:
        count = 1
        while count <= size:
            res.append(count)
            count = count + 1
    return res


def search_text(text, comp):
    count = 0
    sp_text = text.lower().split()
    sp_comp = comp.lower().split()
    comp_count = len(sp_text)
    for element in sp_text:
        if element in sp_comp:
            count = count + 1
    if count == comp_count:
        return True
    else:
        return False


def success_message(amount):
    if amount > 60:
        success = 'success'
        message = _('Payment completed: The diner has a balance of: <strong>${0}</strong>.').format(amount)
    elif 18 < amount <= 60:
        success = 'warning'
        message = _(
            'Payment completed: The diner has a balance of: <strong>${0}</strong>. We recommend increasing it before reaching a negative balance.').format(
            amount)
    elif 0 < amount <= 18:
        success = 'error'
        message = _(
            'Payment completed: The diner has enough balance only for ONE future reservation. We recommend increasing your balance as soon as possible. Current Balance: <strong>${0}</strong>.').format(
            amount)
    else:
        success = 'error'
        message = _(
            'Payment completed: The diner must increase their balance before making a new reservation. Current Balance: <strong>${0}</strong>.').format(
            amount)
    return success, message


def reservation_message(diner, amount):
    if amount > 60:
        class_alert = 'success'
        msg = _('The diner: <strong>{0}</strong> has a balance of: <strong>${1}</strong>.').format(diner, amount)
    elif 18 < amount <= 60:
        class_alert = 'warning'
        msg = _(
            'The diner: <strong>{0}</strong> has a balance of: <strong>${1}</strong>. We recommend increasing it before reaching a negative balance.').format(
            diner, amount)
    elif 0 < amount <= 18:
        class_alert = 'error'
        msg = _(
            'The diner: <strong>{0}</strong> has enough balance only for ONE future reservation. We recommend increasing your balance as soon as possible. Current Balance: <strong> ${1}</strong>.').format(
            diner, amount)
    else:
        class_alert = 'error'
        msg = _(
            'The diner: <strong>{0}</strong>, must increase their balance before making a new reservation. Current Balance: strong>${1}</strong>.').format(
            diner, amount)
    return class_alert, msg


def reservation_plufify(queryset):
    text = '<strong class="reservation_person">{0}</strong>'.format(queryset.first().person)
    if queryset.count() > 0:
        text = ', '.join(
            ['<strong {0}>{1}</strong>'.format(
                '' if not element.person else 'class="reservation_person"',
                element.reservation_category.name if not element.person else element.person)
                for element in queryset])
    return text


def categoty_plurify(category_list):
    text = '<strong>{0}</strong>'.format(category_list[0])
    if len(category_list) > 0:
        text = ', '.join(['<strong>{0}</strong>'.format(element) for element in category_list])
    return text


def context_action(modeladmin, queryset, request, title, value_form, value_action):
    opts = modeladmin.model._meta
    context = {
        **modeladmin.admin_site.each_context(request),
        'title': title,
        'queryset': queryset,
        'opts': opts,
        'action_checkbox_name': helpers.ACTION_CHECKBOX_NAME,
        'value_form': value_form,
        'value_action': value_action,
        'media': modeladmin.media,
    }
    request.current_app = modeladmin.admin_site.name
    return context


def pay_until_top(amount):
    return AMOUNT_TOP if amount > AMOUNT_TOP else amount
