from django.core.management.base import BaseCommand

from diners.apps.reservation.models import Reservation, ReservationCategory


class Command(BaseCommand):
    help = 'Borra todos los ids de personas que no sean de categoria particular'

    def handle(self, *args, **options):
        self.stdout.write("")
        self.stdout.write("BUSCANDO LAS RESERVACIONES QUE NO SEAN DE CATEGORIA PARTICULAR:")
        cat = ReservationCategory.objects.filter(name__contains="Particular").first()
        reservations = Reservation.objects.exclude(reservation_category=cat)
        self.stdout.write("                     BUSQUEDA COMPLETADA")
        self.stdout.write("""ELIMINANDO IDS EN EL CAMPO 'persona':""")
        for reservation in reservations:
            reservation.person = None
        Reservation.objects.bulk_update(reservations,['person'])
        self.stdout.write("                     ELIMINACION COMPLETADA")
