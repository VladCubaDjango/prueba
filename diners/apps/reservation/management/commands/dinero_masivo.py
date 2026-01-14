from django.core.management.base import BaseCommand


class Command(BaseCommand):
    def handle(self, *args, **options):
        from django.conf import settings

        GRAPHQL_SERV = settings.GRAPHQL_SERVICE

        lista = [
            {"id_person": 1, "cantidad": 15.00},
            {"id_person": 2, "cantidad": 15.00},
            {"id_person": 3, "cantidad": 15.00},
        ]
        error = []

        for elem in lista:
            try:
                men = GRAPHQL_SERV.create_transaction(
                    action='diners_reservation_reservation_retrieve',
                    amount=float(elem["cantidad"]),
                    description='Mensaje por definir',
                    person=elem["id_person"],
                    type='CR',
                    user='admin'
                )
                print(men)
            except:
                error.append({"id_person": elem["id_person"], "cantidad": elem["cantidad"]})
        print("      ")
        print("      ")
        print("ERRORES")
        print(error)
        print("      ")
        print("      ")
        print("Fin")
