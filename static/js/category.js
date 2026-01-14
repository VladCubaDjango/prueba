window.addEventListener("load", change_dates);


async function change_dates() {
    const table_list = document.getElementById('result_list');
    if (table_list) {
        const tBody = table_list.getElementsByTagName('tbody')[0];
        const tableRow = tBody.getElementsByTagName('tr');

        const query = 'query getDiningRoomById($id: ID) {diningRoomById(id: $id) {name}}';
        for (let t = 0; t < tableRow.length; t++) {
            const id = tableRow[t].getElementsByClassName('field-dining_room')[0].innerHTML;
            if (id !== '0' && id !== '-') {
                resp = (await connect_post_identity(query, {id: id}, false))
                dining_room = resp.data.diningRoomById
                tableRow[t].getElementsByClassName('field-dining_room')[0].innerHTML = dining_room.name;
            } else {
                if (id !== '0') {
                    tableRow[t].getElementsByClassName('field-dining_room')[0].innerHTML = 'Todos';
                }else{
                    tableRow[t].getElementsByClassName('field-dining_room')[0].innerHTML = '-';
                }
            }
        }

        let resp_json = null;
        const res = await fetch('/reservation/reservationcategory/menu-dates-available/', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie("csrftoken")
            }
        }).catch(error => console.log(error));
        if (res) {
            if (res.ok) {
                resp_json = (await res.json()).list;
                if (resp_json.length > 0) {
                    success_date(resp_json)
                } else {
                    error_date("No hay menus para reservar.")
                }
            } else {
                error_date("ERROR Interno del Servidor. Contacte a los administradores del sistema.")
            }
        } else {
            error_date("Problema con la conexión. Contacte al Administrador del sistema.")
        }
    }

}

function error_date(error_text) {
    var modal = document.getElementById('reserv_especial_group');
    while (modal.firstChild) {
        modal.removeChild(modal.firstChild);
    }
    ;
    try {
        var img = "{% static "
        img / disconnect.png
        " %}"
    } catch (e) {
        var img = ""
    }
    text = ""
    if (img != "") {
        text += "<img src=\"" + img + "\" width=\"100%\" height=\"100%\">\n" +
            "                    </div>\n"
    } else {
        text += "<br><br>"
    }
    text += "<h1 align=\"center\">" + error_text + "</h1>\n" +
        "<div class=\"container-fluid\"><div class=\"row\"><div class=\"col\" align=\"right\">" +
        "<a  href=\"#\" rel=\"modal:close\">Cerrar</a></div></div></div>";

    modal.innerHTML = text
}

function success_date(list) {
    var modal = document.getElementById('reserv_especial_group');
    while (modal.firstChild) {
        modal.removeChild(modal.firstChild);
    }
    HTML_to_print = "<div id=\"data_modal\">\n" +
        "      <h1>Añadir Reservaciones de Categorías:</h1>\n" +
        "     <form>\n" +
        "         <div>\n" +
        "            <div id=\"dialog_date\">" +
        "            </div>" +
        "            <fieldset class=\"module aligned\">\n" +
        "                <div class=\"form-row\">\n" +
        "                    <div>\n" +
        "                        <label class=\"required\" for=\"date_modal\">\n" +
        "                           Fecha:\n" +
        "                       </label>\n" +
        "                       <select id=\"date_modal\" name=\"date\" required=\"\">"
    for (var i = 0; i < list.length; i++) {
        HTML_to_print += "<option value=\"" + list[i].date + "\">" + list[i].text + "</option>\n"
    }
    HTML_to_print += "                      </select>\n" +
        "                   </div>\n" +
        "               </div>\n" +
        "           </fieldset>\n" +
        "           <div class=\"submit-row\">\n" +
        "                <input type=\"button\" onclick=\"reserv_categories()\" value=\"Reservar\">\n" +
        "           </div>\n" +
        "        </div>\n" +
        "      </form>\n" +
        "   </div>";
    modal.innerHTML = HTML_to_print
}

async function reserv_categories() {
    delete_dialog()
    dialog_print("loandingnote", "Reservando. Por favor espere...")
    let resp_json = null;
    const res = await fetch('/reservation/reservationcategory/generate-reserv-categ/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie("csrftoken")
        },
        body: JSON.stringify({'date': document.getElementById("date_modal").value})
    }).catch(error => console.log(error));
    if (res) {
        try {
            resp_json = await res.json();
            delete_dialog()
            if (resp_json.message.successnote) {
                dialog_print("successnote", resp_json.message.successnote)
            }
            if (resp_json.message.warningnote) {
                dialog_print("warningnote", resp_json.message.warningnote)
            }
            if (resp_json.message.errornote) {
                dialog_print("errornote", resp_json.message.errornote)
            }
        } catch (e) {
            delete_dialog()
            dialog_print("errornote", "ERROR Interno del Servidor. Contacte a los administradores del sistema.")
        }
    } else {
        delete_dialog()
        dialog_print("errornote", "Problema con la conexión. Contacte al Administrador del sistema.")
    }
    setTimeout(delete_dialog, 10000)
}

function dialog_print(class_dialog, text) {
    document.getElementById("dialog_date").innerHTML += "<p class=\"" + class_dialog + "\">" + text + "</p>\n"
}

function delete_dialog() {
    document.getElementById("dialog_date").innerHTML = ""
}