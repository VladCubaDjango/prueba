import json

from dal import autocomplete
from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse, HttpResponseForbidden
from django.views import View

from requests.exceptions import RequestException
from django.contrib import messages
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _
from decimal import *
from diners.utils.helpers import isDietText
from diners.apps.reservation.models import Reservation

GRAPHQL_SERV = settings.GRAPHQL_SERVICE


class PersonAutocompleteView(autocomplete.Select2ListView):
    def get_list(self):
        return cache.get('all-person')


class ProcessOperationView(View):
    def get(self, request, *args, **kwargs):
        return HttpResponseForbidden()

    def post(self, request, *args, **kwargs):
        result = json.loads(request.body)
        id = int(result['id'])
        resp = GRAPHQL_SERV.get_transaction_id_all(id)
        if resp:
            return JsonResponse(resp.json(), status=resp.status_code)
        else:
            return JsonResponse({'error': 'No se puede conectar a la api'}, status=400)


class PersonOperationView(View):
    def get(self, request, *args, **kwargs):
        return HttpResponseForbidden()

    def post(self, request, *args, **kwargs):
        result = json.loads(request.body)
        id = int(result['id'])
        resp = GRAPHQL_SERV.get_idTransactions_by_idPerson(id)
        if resp:
            return JsonResponse(resp.json(), status=resp.status_code)
        else:
            return JsonResponse({'error': 'No se puede conectar a la api'}, status=400)


class DinersView(View):
    def get(self, request, *args, **kwargs):
        return HttpResponseForbidden()

    def post(self, request, *args, **kwargs):
        if request.user:
            if request.user.has_perm('people.all_view_diners'):
                try:
                    response = GRAPHQL_SERV.get_diners_data_api()
                except RequestException:
                    return JsonResponse({'error': 'No se puede conectar a la api'}, status=400)
                json_res = response.json()["data"]["allDiners"]
            elif request.user.has_perm('people.area_view_diners'):
                try:
                    response = GRAPHQL_SERV.get_idsPersons_and_area_by_idPerson(request.user.person)
                except RequestException:
                    return JsonResponse({'error': 'No se puede conectar a la api'}, status=400)
                json_res = response.json()["data"]["personById"]["area"]["personSet"]
                formated_list = [{"person": d} for d in json_res]
                json_res = formated_list
            else:
                try:
                    response = GRAPHQL_SERV.get_id_and_name_and_nameArea_by_idPerson(request.user.person)
                except RequestException:
                    return JsonResponse({'error': 'No se puede conectar a la api'}, status=400)
                json_res = response.json()["data"]["personById"]
                formated_list = [{"person": json_res}]
                json_res = formated_list
            if response.json().get("errors"):
                self.message_user(request, _('There is corrupted data. Consult the administrator.'), messages.ERROR)
        persons = []
        for data in json_res:
            dat = data["person"]
            if dat["isActive"]:
                if dat["dinerRelated"]:
                    if dat["expirationDate"] == None:
                        if dat["advancepaymentRelated"] != None:
                            if dat["advancepaymentRelated"]['balance'] == None:
                                persons.append({
                                    "id": dat['id'],
                                    "name": dat['name'],
                                    "area": dat['area']['name'],
                                    "diningRoom": dat["dinerRelated"]['diningRoom']['name'],
                                    "isDiet": isDietText(dat["dinerRelated"]['isDiet']),
                                    "paymentMethod": _("advanced payment").capitalize(),
                                    "amount": "CORRUPTO",
                                })
                            else:
                                if dat["dinerRelated"]['paymentMethod'] == "AP":
                                    persons.append({
                                        "id": dat['id'],
                                        "name": dat['name'],
                                        "area": dat['area']['name'],
                                        "diningRoom": dat["dinerRelated"]['diningRoom']['name'],
                                        "isDiet": isDietText(dat["dinerRelated"]['isDiet']),
                                        "paymentMethod": _("advanced payment").capitalize(),
                                        "amount": Decimal(dat["advancepaymentRelated"]['balance']),
                                    })
                                else:
                                    persons.append({
                                        "id": dat['id'],
                                        "name": dat['name'],
                                        "area": dat['area']['name'],
                                        "diningRoom": dat["dinerRelated"]['diningRoom']['name'],
                                        "isDiet": isDietText(dat["dinerRelated"]['isDiet']),
                                        "paymentMethod": _("card payment").capitalize(),
                                        "amount": "----------",
                                    })
                    else:

                        persons.append({
                            "id": dat['id'],
                            "name": dat['name'],
                            "area": dat['area']['name'],
                            "diningRoom": dat["dinerRelated"]['diningRoom']['name'],
                            "isDiet": isDietText(dat["dinerRelated"]['isDiet']),
                            "paymentMethod": _("card payment").capitalize(),
                            "amount": "TEMPORAL",
                        })
        return JsonResponse({'diners': persons}, status=200)



