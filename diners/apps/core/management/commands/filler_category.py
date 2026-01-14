from django.core.management.base import BaseCommand
from django.conf import settings

from diners.apps.reservation.models import Reservation, ReservationCategory

GRAPHQL_SERV = settings.GRAPHQL_SERVICE


class Command(BaseCommand):
    help = 'Este comando rellena las categorías de las reservaciones organizandolos por reservaciones de grupo o personal.'

    def handle(self, *args, **options):
        resp_json = GRAPHQL_SERV.get_all_Person_position_api().json()["data"]["allPerson"]
        filters = [
            {"text": "GEISEL", "id": [], "cat": True, "name": "GEISEL"},
            {"text": "Escolta", "id": [], "cat": True, "name": "Escolta"},
            {"text": "Monitor", "id": [], "cat": False},
            {"text": "Secretaria", "id": [], "cat": True, "name": "Secretaría"},
            {"text": "Invitado", "id": [], "cat": True, "name": "Invitado"},
            {"text": "Periodista", "id": [], "cat": True, "name": "Prensa"},
            {"text": "Gastronomico", "id": [], "cat": False},
            {"text": "COPEXTEL", "id": [], "cat": False},
            {"text": "EPROB", "id": [], "cat": False},
            {"text": "Chofer", "id": [], "cat": False},
            {"text": "Enfermera", "id": [], "cat": True, "name": "Enfermería"},
        ]
        self.stdout.write("BUSCANDO LOS ID(S) por FILTRO.")
        self.stdout.write(" ")
        for data in resp_json:
            for filt in filters:
                if filt["text"] in data["name"]:
                    filt["id"].append(data["id"])
        for filt in filters:
            self.stdout.write(" ->"+filt["text"] + " - " + str(len(filt["id"])))
        self.stdout.write("")
        self.stdout.write("ARCHIVANDO CATEGORIAS ESPECIALES")
        self.stdout.write("")
        for filt in filters:
            self.stdout.write(" ->procensando: " + filt["text"])
            reservation = Reservation.objects.filter(person__in=filt["id"])
            if filt["cat"]:
                reservation.update(reservation_category=ReservationCategory.objects.filter(name__contains=filt["name"]).first())
                self.stdout.write("       categaorizado: " + filt["name"])
            else:
                reservation.delete()
                self.stdout.write("       borrado")
        self.stdout.write("")
        self.stdout.write("ARCHIVANDO PERSONAS")
        self.stdout.write("")
        reservation = Reservation.objects.filter(reservation_category__isnull=True)
        reservation.update(reservation_category=ReservationCategory.objects.filter(name__contains="Particular").first())
        self.stdout.write("")
        self.stdout.write("COMPROBANDO CATEGORIZACION")
        self.stdout.write("")
        if len(Reservation.objects.filter(reservation_category__isnull=True)) == 0:
            self.stdout.write(" -> Categorización exitosa")
        else:
            self.stdout.write(" -> Existen reservaciones sin categorizar")
        self.stdout.write("")
        self.stdout.write("FINALIZADO")
