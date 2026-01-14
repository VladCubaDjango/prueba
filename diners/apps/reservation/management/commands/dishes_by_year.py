from django.core.management.base import BaseCommand
from django.db.models import Q
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table

from diners.apps.reservation.models import Dish


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            'from_date',
            type=str,
            help='Fecha de comienzo, debe estar en el formato "yyyy-mm-dd".'
        )
        parser.add_argument(
            'to_date',
            type=str,
            help='Fecha de fin, debe estar en el formato "yyyy-mm-dd".'
        )

    def handle(self, *args, **options):
        date_q = Q(menu__date__range=[options['from_date'], options['to_date']])
        is_confirmed = Q(is_confirmed=True)
        data = []

        dishes = Dish.objects.all()
        for dish in dishes:
            plan = dish.reservation_set.filter(date_q).count()
            if plan > 0:
                real = dish.reservation_set.filter(is_confirmed & date_q).count()
                dif = plan - real
                real_percent = (real / plan) * 100
                dif_percent = 100 - real_percent
                data.append([dish.name, plan, real, dif, '{:.2f}%'.format(real_percent), '{:.2f}%'.format(dif_percent)])

        doc = SimpleDocTemplate('platos.pdf')
        story = []
        data_table = [
            ['Plato', 'Plan', 'Real', 'Diferencia', '% Real', '% Diferencia'],
        ]
        data.sort(key=lambda l: l[4], reverse=True)
        data_table += data
        table = Table(data=data_table, style=[
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BOX', (0, 0), (-1, -1), 2, colors.black),
            ('BACKGROUND', (0, 0), (-1, 0), colors.pink),
        ])
        story.append(table)
        doc.build(story)
