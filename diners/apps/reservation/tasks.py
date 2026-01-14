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
