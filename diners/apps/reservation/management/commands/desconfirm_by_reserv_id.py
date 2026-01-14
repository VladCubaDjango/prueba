from django.core.management.base import BaseCommand


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            'reserv_id',
            type=int,
            help='The reservation id'
        )

    def handle(self, *args, **options):
        from diners.apps.reservation.models import Reservation

        reserv = Reservation.objects.get(id=options['reserv_id'])
        reserv.is_confirmed = False
        reserv.save()
        self.stdout.write(self.style.SUCCESS('Se desconfirmó {}'.format(str(reserv))))
