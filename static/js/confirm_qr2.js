local_qr = localStorage.getItem("camera_person")
var qr_confirm = null
if (local_qr != null) {
    qr_confirm = JSON.parse(local_qr).qr
}

window.addEventListener("load", to_confirm);

async function to_confirm() {
    while (true) {
        local = localStorage.getItem("camera_person")
        if (local != null) {
            local_qr = JSON.parse(local)
            if (local_qr.qr != qr_confirm) {
                qr_confirm = local_qr.qr
                if (local_qr.windows == "reserv_confirm") {
                    confirm_QR_person(qr_confirm)
                }
            }
        }
        await timeout(500);
    }
}

async function confirm_QR_person(code_qr) {
    let resp_json = null;
    const query_person = "id,name,dinerRelated{isActive,paymentMethod},advancepaymentRelated{balance}"
    const person = await getPersonFromCamera(query_person, code_qr);
    if (person.data != null) {
        while (resp_json == null) {
            const res = await fetch('/reservation/reservation/confirm_person/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie("csrftoken")
                },
                body: JSON.stringify(person)
            }).catch(error => console.log(error));
            if (res) {
                if (res.ok) {
                    resp_json = (await res.json()).list;
                    if (resp_json.type === "error") {
                        showListMessages(resp_json)
                        await timeout(5000);
                    } else {
                        cameraConfirm(resp_json)
                    }
                } else {
                    showMessage("error", "Error interno en el servidor. Contacte al Administrador")
                    await timeout(5000);
                }
            } else {
                showMessage("error", "Problema con la conexión. Contacte al Administrador. Confirm QR")
                await timeout(5000);
            }
        }
    }
}

function cameraConfirm(data) {
    showListMessages(data)
    local = localStorage.getItem("camera_info")
    id_info_v = 0
    if (local != null) {
        id_info_v = JSON.parse(local).id_info + 1
    }


    if (data[0].type == "success") {
        row = document.getElementById("check_" + data[0].reserv)
        console.log(row)
        if (row != null) {
            row.classList.remove("uncheck")
            row.classList.add("check")
        }

        reserv_info_modal(data[0].reserv, data[0].name)
        footer_html = ""
        if (data.length > 1) {
            footer_html = html_qr_footer(data[1].type, data[1].balance)
        } else {
            footer_html = "Pago por tarjeta"
        }
        localStorage.setItem("camera_info", JSON.stringify({
            id_info: id_info_v,
            name: data[0].name,
            date: data[0].date,
            body: html_qr_body(data[0].type, data[0].dishes),
            left_footer: "CONFIRMADO",
            rigt_footer: footer_html,
            page_foot: "¡Buen Provecho!"
        }))
    } else {
        localStorage.setItem("camera_info",
            JSON.stringify({
                id_info: id_info_v,
                name: "",
                date: "",
                body: html_qr_body(data[0].type, data[0].mess),
                left_footer: "",
                rigt_footer: "",
                page_foot: ""
            }))
    }


}

function html_qr_body(type, data) {
    html_resp = "<div class=\"colmn-block\">"
    if (type == "success") {
        total = 0.00
        for (var i = 0; i < data.length; i++) {
            html_resp = html_resp + "<p>\n" +
                "                       <span class=\"elem-left\">" + data[i].dish + "</span>\n" +
                "                       <span class=\"elem-rigth\">$" + data[i].price + "</span>\n" +
                "                    </p>"
            total = total + parseFloat(data[i].price)
        }
        html_resp = html_resp + "<p>\n" +
            "                       <span class=\"elem-left total-p\">TOTAL</span>\n" +
            "                       <span class=\"elem-rigth total-p\">$" + total.toFixed(2) + "</span>\n" +
            "                    </p>"
    } else {
        html_resp = "<div class=\"colmn-block body_error\"><p align=\"center\">" + data + "</p>"
    }
    html_resp = html_resp + "</div>"
    return html_resp
}

function html_qr_footer(type, data) {
    html_type = ""
    switch (type) {
        case "success":
            html_type = "money-success";
            break;
        case "error":
            html_type = "money-error";
            break;
        case "warning":
            html_type = "money-warning";
            break;
    }
    return "Saldo: <span class=\"" + html_type + "\">$" + data + "</span>"
}

function manualConfirm(data) {
    local = localStorage.getItem("camera_info")
    id_info_v = 0
    if (local != null) {
        id_info_v = JSON.parse(local).id_info + 1
    }

    if (data.type == "success") {
        footer_html = ""
        if (data.person) {
            footer_html = html_qr_footer(data.person.type, data.person.balance)
        } else {
            footer_html = "Pago por tarjeta"
        }

        localStorage.setItem("camera_info", JSON.stringify({
            id_info: id_info_v,
            name: data.name,
            date: data.date,
            body: html_qr_body(data.type, data.dishes),
            left_footer: data.action_text.toUpperCase(),
            rigt_footer: footer_html,
            page_foot: "¡Buen Provecho!"
        }))
    } else {
        localStorage.setItem("camera_info", JSON.stringify({
            id_info: id_info_v,
            name: "",
            date: "",
            body: html_qr_body(data.type, data.mess),
            left_footer: "",
            rigt_footer: "",
            page_foot: ""
        }))
    }


}