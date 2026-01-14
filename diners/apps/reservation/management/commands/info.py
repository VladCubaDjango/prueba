from django.core.management.base import BaseCommand


class Command(BaseCommand):
    def handle(self, *args, **options):
        import datetime
        from diners.apps.reservation.models import Reservation
        from diners.apps.reservation.models import MealSchedule
        from django.conf import settings
        GRAPHQL_SERV = settings.GRAPHQL_SERVICE

        areas = GRAPHQL_SERV.get_allperson_for_allareas()
        iterations = [
            {"mes": "Abril", "fecha_ini": datetime.datetime.strptime('01/04/2023', '%d/%m/%Y'),
             "fecha_fin": datetime.datetime.strptime('01/05/2023', '%d/%m/%Y')},
            {"mes": "Mayo", "fecha_ini": datetime.datetime.strptime('01/05/2023', '%d/%m/%Y'),
             "fecha_fin": datetime.datetime.strptime('01/06/2023', '%d/%m/%Y')},
        ]
        print("CARGANDO HORARIOS")
        shedules = MealSchedule.objects.all()
        print("SE HAN CARGADO " + str(shedules.count()) + " HORARIOS")
        print("------------------------------------------------------")
        print("------------------------------------------------------")
        print("------------CARGANDO LA INFORMACION")
        for iter in iterations:
            print("" + iter["mes"])
            print(" ")
            for shedul in shedules:
                reservations = Reservation.objects.filter(menu__date__gte=iter["fecha_ini"]).filter(
                    menu__date__lte=iter["fecha_fin"]).filter(menu__schedule=shedul).prefetch_related('dishes')
                total = reservations.count()
                confirmado = reservations.filter(is_confirmed=True).count()
                areas_no_conf={}
                print("" + shedul.name + "("+str(total)+"-"+str(confirmado)+"-"+str(total-confirmado)+")")
                print("**")
                # cache areas JSON to avoid repeated calls
                areas_json = areas.json()["data"]["allAreas"]
                for reservation in reservations.filter(is_confirmed=False):
                    for area in areas_json:
                        for person in area["personSet"]:
                            if str(reservation.person) == person["id"]:
                                if area["name"] in areas_no_conf:
                                    areas_no_conf[area["name"]]=areas_no_conf[area["name"]]+1
                                else:
                                    areas_no_conf[area["name"]]=1
                llaves = areas_no_conf.keys()
                for llave in llaves:
                    print(llave+" ----> "+str(areas_no_conf[llave]))


