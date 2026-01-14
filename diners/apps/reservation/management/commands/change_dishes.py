from django.core.management.base import BaseCommand


class Command(BaseCommand):
    def handle(self, *args, **options):
        from diners.apps.reservation.models import Reservation
        from diners.apps.reservation.models import Menu
        from diners.apps.reservation.models import Dish
        from diners.utils.helpers import sum_price_dishes
        from django.conf import settings
        from django.db.models import Q

        GRAPHQL_SERV = settings.GRAPHQL_SERVICE

        menus = [
            4082,
            4086,
        ]
        for menu in menus:
            real_menu = Menu.objects.get(id=menu)
            condition = Q(menu=real_menu)
            reservations = Reservation.objects.filter(condition)

            # prefetch dishes to avoid N+1 queries and reduce DB roundtrips
            for reservation in reservations.prefetch_related('dishes'):
                price_to_change = 0
                tiene_natilla = False
                for dish in reservation.dishes.all():
                    # price_to_change = price_to_change + dish.price
                    # if not tiene_natilla and dish.name == "Natilla de Vainilla":
                    if dish.name == "Pan Redondo Duro":
                        tiene_natilla = True
                        price_to_change = dish.price
                        # reservation.dishes.add(Dish.objects.filter(name__exact="Pan con Queso")[0])
                        # reservation.dishes.remove(dish)
                # print(price_to_change)
                # if not tiene_natilla:
                #     reservation.dishes.add(Dish.objects.filter(name__exact="Natilla de Vainilla")[0])
                # if price_to_change < 18:
                        id = reservation.person
                        borrar = True
                        if id !=None:
                            diner = GRAPHQL_SERV.get_diner_api(id).json()['data']['dinerById']
                            if diner:
                                payment_method = diner['paymentMethod']
                                if payment_method == 'AP':
                                    # if price_to_change == 17:
                                    #     cantidad = 1
                                    # else:
                                    #     cantidad = 2
                                    try:
                                        GRAPHQL_SERV.create_transaction(
                                            action='diners_reservation_reservation_change_menu',
                                            amount=float(price_to_change),
                                            description='Cambio de platos autorizado por Yamicela, Jefa del Comedor',
                                            person=id,
                                            type='CR',
                                            user='admin'
                                        )
                                    except:
                                        print(str(id)+" -------- "+str(price_to_change))
                                        borrar=False
                        if borrar:
                            reservation.dishes.remove(dish)

                # if dish not in real_menu.dishes.all():
                #     new_dish = None
                #     for elem in real_menu.dishes.all():
                #         if dish.dish_category == elem.dish_category:
                #             new_dish=elem
                #     if new_dish==None:
                #         price_to_change = price_to_change-dish.price
                #         reservation.dishes.remove(dish)
                #     else:
                #         price_to_change = price_to_change+dish.price-new_dish.price
                #         reservation.dishes.remove(dish)
                #         reservation.dishes.add(new_dish)
                # if price_to_change < 0:
                #     trans_type = 'DB'
                #     price_to_change = price_to_change*-1
                # elif price_to_change > 0:
                #     trans_type = 'CR'
                # id = reservation.person
                # if id !=None:
                #     diner = GRAPHQL_SERV.get_diner_api(id).json()['data']['dinerById']
                #     payment_method = diner['paymentMethod']
                #     if payment_method == 'AP' and price_to_change!=0:
                #         try:
                #             GRAPHQL_SERV.create_transaction(
                #                 action='diners_reservation_reservation_change_menu',
                #                 amount=float(price_to_change),
                #                 description='Cambio de platos autorizado por Yamicela, Jefa del Comedor',
                #                 person=id,
                #                 type=trans_type,
                #                 user='admin'
                #             )
                #         except:
                #             print(id+" -------- "+str(price_to_change))
