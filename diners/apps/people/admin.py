import copy
from decimal import *

from decouple import config
from django.conf import settings
from django.contrib import admin
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import path
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _
from requests.exceptions import RequestException

from diners.utils.helpers import isDietText, formatDateOperations, typeOperationText
from .forms import UserChangeMixinForm, UserCreationMixinForm, OperationForm
from .views import ProcessOperationView, PersonAutocompleteView, PersonOperationView, DinersView

User = get_user_model()
GRAPHQL_SERV = settings.GRAPHQL_SERVICE


@admin.register(User)
class UserAdmin(UserAdmin):
    form = UserChangeMixinForm
    add_form = UserCreationMixinForm

    def get_fieldsets(self, request, obj=None):
        fieldsets = copy.deepcopy(super().get_fieldsets(request, obj))
        fieldsets += (
            (_('person'), {
                'fields': ['person']}),
        )
        return fieldsets

    def get_model_info(self):
        app_label = self.model._meta.app_label
        model_name = self.model._meta.model_name
        return app_label, model_name

    def get_urls(self):
        urls = super().get_urls()
        _urls = [
            path('diner/', self.admin_site.admin_view(self.diner_view), name='%s_%s_diner' % self.get_model_info()),
            path('process-operation/', self.admin_site.admin_view(ProcessOperationView.as_view()),
                 name='%s_%s_diner_token' % self.get_model_info()),
            path('diners-data/', self.admin_site.admin_view(DinersView.as_view()),
                 name='%s_%s_diners_data' % self.get_model_info()),
            path('personcomplete/', self.admin_site.admin_view(PersonAutocompleteView.as_view()),
                 name='%s_%s_personcomplete' % self.get_model_info()),
            path('existOperation/', self.admin_site.admin_view(PersonOperationView.as_view()),
                 name='%s_%s_existoperation' % self.get_model_info()),
        ]
        return _urls + urls

    def diner_view(self, request):
        if request.GET.get('person_operations', default=None)!=None:
            request.current_app = self.admin_site.name
            context = dict(self.admin_site.each_context(request))
            context['title'] = _('operations').capitalize()
            context['opts'] = self.model._meta

            context['operations_headers'] = [
                _('date').capitalize(),
                _('type').capitalize(),
                _('amount').capitalize(),
            ]

            id_person = request.GET['person_operations']
            perms = True
            if request.user.has_perm('people.area_view_diners') and not request.user.is_superuser:
                try:
                    list_id = GRAPHQL_SERV.get_idsPersons_of_area_by_idPerson(request.user.person)
                except RequestException:
                    self.message_user(request, _('Connection error. Contact the system administrators.'),
                                      messages.ERROR)
                    return HttpResponseRedirect('/')
                json_list_id = list_id.json()["data"]["personById"]["area"]["personSet"]
                if id_person not in [dat['id'] for dat in json_list_id]:
                    perms = False
            elif not request.user.has_perm('people.all_view_diners') and int(
                    id_person) != request.user.person and not request.user.is_superuser:
                perms = False
            if perms:
                try:
                    response_per = GRAPHQL_SERV.get_dataTransactions_by_idPerson_api(id_person)
                except RequestException:
                    self.message_user(request, _('Connection error. Contact the system administrators.'),
                                      messages.ERROR)
                    return HttpResponseRedirect('/')
                json_res_per = response_per.json()["data"]["personById"]
                context['person_name'] = json_res_per["name"]
                operations = []
                for dat in response_per.json()["data"]["personById"]["transactionSet"]:
                    operations.append({
                        "id": dat["id"],
                        "datetime": formatDateOperations(dat["datetime"]),
                        "type": typeOperationText(dat["type"]),
                        "amount": dat["amount"],
                    })

                context['operations'] = operations
                context['api_url'] = config('API_URL')

                return TemplateResponse(request, 'people/operation_template.html', context)
            else:
                self.message_user(request,
                                  _('You do not have permission to view the operations of the selected user.'),
                                  messages.ERROR)

        request.current_app = self.admin_site.name
        context = dict(self.admin_site.each_context(request))
        context['title'] = _('diners and operations').capitalize()
        context['opts'] = self.model._meta
        context['form_operation'] = OperationForm()


        return TemplateResponse(request, 'people/person_template.html', context)
