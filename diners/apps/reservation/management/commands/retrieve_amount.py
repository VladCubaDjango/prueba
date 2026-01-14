from django.core.management.base import BaseCommand


class Command(BaseCommand):
    def handle(self, *args, **options):
        from diners.apps.reservation.models import Reservation
        from diners.apps.reservation.models import Menu
        from diners.utils.helpers import sum_price_dishes
        from django.conf import settings
        from django.db.models import Q

        GRAPHQL_SERV = settings.GRAPHQL_SERVICE

        condition = Q(menu=Menu.objects.get(id=3681))
        # prefetch dishes to avoid N+1 queries and cache diner lookups
        reservations = Reservation.objects.filter(condition).prefetch_related('dishes')

        diner_cache = {}
        for reservation in reservations:
            id = reservation.person
            if id:
                print(id)
                diner = diner_cache.get(id)
                if diner is None:
                    diner = GRAPHQL_SERV.get_diner_api(id).json()['data']['dinerById']
                    diner_cache[id] = diner
                print(diner)
                payment_method = diner['paymentMethod']
                amount = sum_price_dishes(reservation.dishes.all())
                # if payment_method == 'AP' and amount > 18:
                if payment_method == 'AP':
                #     dif = amount - 18
                    try:
                        GRAPHQL_SERV.create_transaction(
                            action='diners_reservation_reservation_retrieve',
                            # amount=float(dif),
                            amount=float(amount),
                            description='Devolución del monto de la reserva del almuerzo del 26 de octubre con motivo de la Contingencia Energética a nivel de país',
                            person=id,
                            type='CR',
                            user='admin'
                        )
                        self.stdout.write(self.style.SUCCESS('{} se le va a devolver {}'.format(diner['person']['name'], amount)))
                    except Exception:
                        # log and continue with next reservation
                        self.stderr.write('create_transaction failed for person {}'.format(id))
