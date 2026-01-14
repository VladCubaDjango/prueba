from dal import autocomplete
from django import forms
from django.conf import settings
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.core.cache import cache
from django.utils.translation import gettext_lazy as _

GRAPHQL_SERV = settings.GRAPHQL_SERVICE


class MixinForm(forms.ModelForm):
    person = autocomplete.Select2ListCreateChoiceField(
        required=True,
        label=_('person').capitalize(),
        widget=autocomplete.ListSelect2(url='admin:people_user_personcomplete')
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        cache.set('all-person', GRAPHQL_SERV.diners_to_choices(), None)
        self.fields['person'].choices = cache.get('all-person')


class UserChangeMixinForm(UserChangeForm, MixinForm):
    pass


class UserCreationMixinForm(UserCreationForm, MixinForm):
    pass


class OperationForm(forms.Form):
    person_operations = forms.IntegerField(label=_('Person operations'))


class PagerPersonal(forms.Form):
    new_page = forms.IntegerField(label=_('Index page'), initial=1)
    filtering = forms.CharField(label=_('Filtering'), required=False, )
