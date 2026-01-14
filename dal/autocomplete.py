from django import forms
from django.views import View
from django.http import JsonResponse

class ListSelect2:
    def __init__(self, url=None, *args, **kwargs):
        self.url = url

class Select2Multiple:
    def __init__(self, url=None, attrs=None, forward=None):
        self.url = url
        self.attrs = attrs or {}
        self.forward = forward

class Select2ListCreateChoiceField(forms.ChoiceField):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class Select2ListView(View):
    """Simple placeholder that returns an empty result list for local development."""
    def get(self, request, *args, **kwargs):
        return JsonResponse({"results": []})
