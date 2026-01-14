from __future__ import absolute_import, unicode_literals
from celery import shared_task
from django.conf import settings

GRAPHQL_SERV = settings.GRAPHQL_SERVICE


@shared_task(bind=True, max_retries=3)
def create_transaction_task(self, action, amount, description, person, type_, user):
    try:
        return GRAPHQL_SERV.create_transaction(
            action=action,
            amount=amount,
            description=description,
            person=person,
            type=type_,
            user=user
        ).json()
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def remove_reservations_for_category_schedule(self, reservation_category_id, mealschedule_id):
    try:
        from diners.apps.reservation.models import Reservation
        from diners.utils.helpers import get_difference_day

        cutoff = get_difference_day()
        Reservation.objects.filter(
            reservation_category_id=reservation_category_id,
            menu__schedule_id=mealschedule_id,
            menu__date__gte=cutoff
        ).delete()
        return True
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)
