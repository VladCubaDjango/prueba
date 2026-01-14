from django.conf import settings
from django.utils.translation import gettext as _
from requests.exceptions import RequestException

from diners.apps.reservation.models import Reservation

GRAPHQL_SERV = settings.GRAPHQL_SERVICE


def isConfirmedHtmlList(request, is_confirmed, id_reservation):
    HTML = ""
    id_r = str(id_reservation)
    reserv = Reservation.objects.get(id=id_r)
    if request.user.has_perm('reservation.confirm_change_reservation') \
            and not reserv.reservation_category.name == "Invitado" \
            and reserv.person_donate == None \
            and reserv.offplan_data == [] \
            :

        HTML += "<div class='"
        if is_confirmed:
            HTML += "check"
        else:
            HTML += "uncheck"
        HTML += " images_13' id='check_" + id_r + "' onclick='change_confirm(" + id_r + ")' onmouseover='focus_check(" + id_r + ")' onmouseout='focus_check(" + id_r + ")'></div>\n"
    else:
        if is_confirmed:
            HTML += '<img src="/static/admin/img/icon-yes.svg" alt="True">'
        else:
            HTML += '<img src="/static/admin/img/icon-no.svg" alt="False">'
    return HTML


def moreActionReservationHtml(request, id_reservation):
    HTML = ""
    id_r = str(id_reservation)
    reserv = Reservation.objects.get(id=id_r)
    HTML += "<img title=\"Ver más información\" class=\"info-button padding-action\" data-id=\"" + id_r + "\" src=\"/static/img/info-circle.png\" onclick=\"more_info(event)\" width=\"20\">"
    if request.user.has_perm('reservation.delete_reservation'):
        HTML += "<img title=\"Cancelar reservación.\" style=\"cursor: pointer;\" src =\"/static/img/trash-o.png\" onclick='delete_reserv_modal(" + id_r + ")' width=\"20\">\n"
    if reserv.reservation_category.name == "Invitado" and not reserv.is_confirmed and request.user.has_perm(
            'reservation.confirm_change_reservation'):
        HTML += "<img style=\"cursor: pointer;\" title=\"Confirmar invitado fuera de plan.\" class=\"invited-button padding-action\" data-id=\"" + id_r + "\" src=\"/static/img/linked-in.png\" onclick=\"invited_offplan_submit(event)\" width=\"20\">"
    if reserv.person and request.user.has_perm('reservation.confirm_change_reservation'):
        HTML += "<img style=\"cursor: pointer;\" title=\"Confirmar fuera de plan.\" class=\"offplan-button padding-action\" data-id=\"" + id_r + "\" src=\"/static/img/comment-dots.png\" onclick=\"offplan_submit(event)\" width=\"20\">"
        HTML += "<img style=\"cursor: pointer;\" title=\"Donar reservacion.\" class=\"donate-button padding-action\" data-id=\"" + id_r + "\" src=\"/static/img/donate.png\" onclick=\"donate_submit(event)\" width=\"20\">"
    return HTML


def getActionsReservations(request):
    response = []
    if request.user.has_perm('reservation.delete_reservation'):
        response.append({"value": "deleteReservations", "text": _("Delete selected reservations")})
    return response


def getQuerySetReservation(request):
    qs = Reservation.objects.all()
    if request.user:
        if request.user.has_perm('reservation.all_view_reservation'):
            pass
        elif request.user.has_perm('reservation.area_view_reservation'):
            try:
                list_person = \
                    GRAPHQL_SERV.get_idsPersons_of_area_by_idPerson(request.user.person).json()['data'][
                        'personById'][
                        'area'][
                        'personSet']
                qs = qs.filter(person__in=[list_id['id'] for list_id in list_person])
            except RequestException:
                qs = None
        else:
            qs = qs.filter(person__exact=request.user.person)
    return qs
