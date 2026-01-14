from django.core.management.base import BaseCommand


class Command(BaseCommand):
    def handle(self, *args, **options):
        from diners.apps.reservation.models import Reservation
        import datetime

        to_confirm = Reservation.objects.filter(
            menu__date__gte=datetime.datetime.strptime('01/01/2023', '%d/%m/%Y')).filter(
            menu__date__lte=datetime.datetime.strptime('31/12/2023', '%d/%m/%Y')).filter(is_confirmed=False).filter(menu__date__week_day__in=[1,7])
        for elem in to_confirm:
            elem.is_confirmed = True
            elem.save()
