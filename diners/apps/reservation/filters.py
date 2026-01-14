import django_filters
from django.conf import settings
from django.core.cache import cache

from .models import Reservation, MealSchedule, ReservationCategory

GRAPHQL_SERV = settings.GRAPHQL_SERVICE
# 2 horas por 60 minutos por 60 segundos
TIME_TO_SAVE = 2 * 60 * 60


class ReservationFilter(django_filters.FilterSet):
    is_confirmed = django_filters.BooleanFilter()
    menu = django_filters.ModelChoiceFilter(
        queryset=MealSchedule.objects.all(),
        lookup_expr="schedule",
    )
    diningroom = django_filters.Filter(
        field_name="person",
        method="DiningRoomDjangoFilter"
    )
    date__gte = django_filters.DateFilter(
        field_name="menu",
        lookup_expr="date__gte"
    )
    date__lte = django_filters.DateFilter(
        field_name="menu",
        lookup_expr="date__lte"
    )
    q = django_filters.Filter(
        field_name="person",
        method="SearchDjangoFilter"
    )

    def DiningRoomDjangoFilter(self, queryset, name, value):
        try:
            cah_dinR = cache.get("diningRoom")
            diner_set_list = None
            if cah_dinR:
                for elem in cah_dinR:
                    if elem["id_diningRoom"] == value:
                        diner_set_list = elem["dinerSet"]
                        break
            else:
                cah_dinR = []
                cache.set("diningRoom", cah_dinR, TIME_TO_SAVE)

            if diner_set_list == None:
                diner_set = GRAPHQL_SERV.get_diners_by_dinningroom(value).json()['data']['diningRoomById']['dinerSet']
                diner_set_list = [list_id['person']['id'] for list_id in diner_set]
                cah_dinR.append({"id_diningRoom": value, "dinerSet": diner_set_list})
                cache.set("diningRoom", cah_dinR, TIME_TO_SAVE)
            queryset_aux = queryset.filter(person__in=diner_set_list)
            cat = ReservationCategory.objects.filter(dining_room=value)
            response = queryset_aux | queryset.filter(reservation_category__in=cat)
        except:
            response = queryset
        return response

    def SearchDjangoFilter(self, queryset, name, value):
        response = None
        try:
            persons = GRAPHQL_SERV.get_person_api_by_name(value).json()['data']['personByName']
            for person in persons:
                if response is None:
                    response = queryset.filter(person__exact=(int(person['id'])))
                else:
                    response = response | queryset.filter(person__exact=(int(person['id'])))
            areas = GRAPHQL_SERV.get_area_api_by_name(value).json()['data']['areaByName']
            for area in areas:
                for person in area["personSet"]:
                    if response is None:
                        response = queryset.filter(person__exact=(int(person["id"])))
                    else:
                        response = response | queryset.filter(person__exact=(int(person["id"])))
            categories = ReservationCategory.objects.all().filter(name__icontains=value)
            if response is None:
                response = queryset.filter(reservation_category__in=categories)
            else:
                response = response | queryset.filter(reservation_category__in=categories)
        except:
            response = queryset
        if response is None:
            response = Reservation.objects.none()
        return response

    class Meta:
        model = Reservation
        fields = ['is_confirmed', "menu", "person", "reservation_category"]
