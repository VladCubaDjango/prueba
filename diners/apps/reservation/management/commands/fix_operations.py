import time

from django.core.management.base import BaseCommand

from diners.apps.reservation.models import Prueba


class Command(BaseCommand):
    def handle(self, *args, **options):
        from diners.apps.reservation.models import Reservation
        from diners.apps.reservation.models import Operation

        operations = Operation.objects.all()
        max_count = operations.count()
        count = 1
        initial_time = time.time()
        for op in operations:
            reservs = op.reservation_set.all()
            for res in reservs:
                porcent = round((count / max_count) * 100)
                count += 1
                # -------------------------------------------------------------
                p = Prueba(id=op.id, reservation=res)
                p.save()
                # -------------------------------------------------------------
                transcurr_time = round(time.time() - initial_time)
                min = int(transcurr_time / 60)
                seg = transcurr_time - (min * 60)
                if seg == 0:
                    seg = "00"
                elif seg < 10:
                    seg = "0" + str(seg)
                else:
                    seg = "" + str(seg)
                print(str(porcent) + "% - " + str(min) + ":" + seg + " - ("+str(op.id)+"<->" + str(res.pk)+")")

