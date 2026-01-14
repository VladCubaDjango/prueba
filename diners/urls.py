from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.utils.translation import gettext_lazy as _
from django.http import JsonResponse, HttpResponseBadRequest

admin.site.site_header = _('Diner management system')

GRAPHQL_SERV = settings.GRAPHQL_SERVICE


def jwt_token(request):
    if request.method == "POST":
        resp = GRAPHQL_SERV.get_token()
        if resp:
            return JsonResponse({'data': resp}, status=200)
        else:
            return JsonResponse({'error': 'ERROR de conexión. Contacte la Administración.'}, status=400)
    else:
        return HttpResponseBadRequest('Request should be from POST method')

urlpatterns = [
                  path('api_token/', jwt_token, name='jwt_token'),
                  path('session_security/', include('session_security.urls')),  # session security
                  path('', admin.site.urls),
              ] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)  # paths to media urls

if settings.DEBUG:
    import debug_toolbar

    urlpatterns = [
                      path('__debug__/', include(debug_toolbar.urls)),
                  ] + urlpatterns
