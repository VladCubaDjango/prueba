from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            'person_id',
            type=int,
            help='The person id'
        )
        parser.add_argument(
            'amount',
            type=float,
            help='Total amount to retrieve'
        )

    def handle(self, *args, **options):


        GRAPHQL_SERV = settings.GRAPHQL_SERVICE

        person_id = options['person_id']
        amount = options['amount']

        GRAPHQL_SERV.create_transaction(
            action='diners_reservation_reservation_retrieve',
            amount=float(amount),
            description='Devolución del monto.',
            person=person_id,
            type='CR',
            user='admin'
        )
        self.stdout.write(self.style.SUCCESS('{} se le va a devolver {}'.format(person_id, amount)))
