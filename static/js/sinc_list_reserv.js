window.addEventListener("load", list_reserv);
window.addEventListener("load", load_links_localstorage);
document.addEventListener("visibilitychange", () => {
    console.log(localStorage.getItem("camera_person"))
    if (document.visibilityState === "visible") {
        change_qr_windows()
    }
})

function change_qr_windows() {
    qr_data = localStorage.getItem("camera_person")
    if (qr_data != null) {
        qr_data_qr = JSON.parse(qr_data).qr
    } else {
        qr_data_qr = null
    }
    localStorage.setItem("camera_person", JSON.stringify({qr: qr_data_qr, windows: "reserv_confirm"}))
}

change_qr_windows()

var filt_search = null

document.getElementsByTagName("html")[0].setAttribute("style", "scroll-behavior: smooth;")

function bool_to_check(bool) {
    if (bool) {
        return "check"
    } else {
        return "uncheck"
    }
}

async function change_page(page) {
    json_data = localStorage.getItem("diners_reservation_list")
    if (json_data) {
        data = JSON.parse(json_data)
        data.sinc_page = page
        localStorage.setItem("diners_reservation_list", JSON.stringify(data))
    } else {
        data = {
            sinc_page: page,
            filt_confirmed: null,
            filt_shedule: null,
            filt_diningroom: null,
            filt_date_gte: null,
            filt_date_lte: null
        }
        localStorage.setItem("diners_reservation_list", JSON.stringify(data))
    }
    list_reserv()
}

function enter_search(e) {
    if (e.keyCode == 13) {
        search()
    }
}

function enter_date_lte(e) {
    if (e.keyCode == 13) {
        filter_date_lte()
    }
}

function enter_date_gte(e) {
    if (e.keyCode == 13) {
        filter_date_gte()
    }
}

function select_link() {
    li = event.target.parentElement
    ul = li.parentElement.children
    for (e = 0; e < ul.length; e++) {
        ul[e].classList.remove("selected")
    }
    li.classList.add("selected")
}

function select_date_link() {
    li = event.target.parentElement.parentElement
    ul = li.parentElement.children
    for (e = 0; e < ul.length; e++) {
        ul[e].classList.remove("selected")
    }
    li.classList.add("selected")
}

function filter_date_gte() {
    val = document.getElementById('date_gte').value
    if (val != "") {
        filt_date_gte = val
    } else {
        filt_date_gte = null
    }
    json_data = localStorage.getItem("diners_reservation_list")
    if (json_data) {
        data = JSON.parse(json_data)
        data.filt_date_gte = filt_date_gte
        data.sinc_page = 1
        localStorage.setItem("diners_reservation_list", JSON.stringify(data))
    } else {
        data = {
            sinc_page: 1,
            filt_confirmed: null,
            filt_shedule: null,
            filt_diningroom: null,
            filt_date_gte: filt_date_gte,
            filt_date_lte: null
        }
        localStorage.setItem("diners_reservation_list", JSON.stringify(data))
    }
    list_reserv()
    select_date_link()
}

function filter_date_lte() {
    val = document.getElementById('date_lte').value
    if (val != "") {
        filt_date_lte = val
    } else {
        filt_date_lte = null
    }
    json_data = localStorage.getItem("diners_reservation_list")
    if (json_data) {
        data = JSON.parse(json_data)
        data.filt_date_lte = filt_date_lte
        data.sinc_page = 1
        localStorage.setItem("diners_reservation_list", JSON.stringify(data))
    } else {
        data = {
            sinc_page: 1,
            filt_confirmed: null,
            filt_shedule: null,
            filt_diningroom: null,
            filt_date_gte: null,
            filt_date_lte: filt_date_lte
        }
        localStorage.setItem("diners_reservation_list", JSON.stringify(data))
    }
    list_reserv()
    select_date_link()
}


function filter_date_range(gte, lte) {
    document.getElementById('date_gte').value = gte
    document.getElementById('date_lte').value = lte
    json_data = localStorage.getItem("diners_reservation_list")
    if (json_data) {
        data = JSON.parse(json_data)
        data.filt_date_gte = gte
        data.filt_date_lte = lte
        data.sinc_page = 1
        localStorage.setItem("diners_reservation_list", JSON.stringify(data))
    } else {
        data = {
            sinc_page: 1,
            filt_confirmed: null,
            filt_shedule: null,
            filt_diningroom: null,
            filt_date_gte: gte,
            filt_date_lte: lte
        }
        localStorage.setItem("diners_reservation_list", JSON.stringify(data))
    }
    list_reserv()
    select_link()
}

function filter_confirmed(val) {
    switch (val) {
        case 0:
            filt_confirmed = "false";
            break;
        case 1:
            filt_confirmed = "true";
            break;
        default:
            filt_confirmed = null
    }
    json_data = localStorage.getItem("diners_reservation_list")
    if (json_data) {
        data = JSON.parse(json_data)
        data.filt_confirmed = filt_confirmed
        data.sinc_page = 1
        localStorage.setItem("diners_reservation_list", JSON.stringify(data))
    } else {
        data = {
            sinc_page: 1,
            filt_confirmed: filt_confirmed,
            filt_shedule: null,
            filt_diningroom: null,
            filt_date_gte: null,
            filt_date_lte: null
        }
        localStorage.setItem("diners_reservation_list", JSON.stringify(data))
    }
    list_reserv()
    select_link()
}

function search() {
    filt_search = document.getElementById('searchbar').value
    json_data = localStorage.getItem("diners_reservation_list")
    if (json_data) {
        data = JSON.parse(json_data)
        data.sinc_page = 1
        localStorage.setItem("diners_reservation_list", JSON.stringify(data))
    } else {
        data = {
            sinc_page: 1,
            filt_confirmed: null,
            filt_shedule: null,
            filt_diningroom: null,
            filt_date_gte: null,
            filt_date_lte: null
        }
        localStorage.setItem("diners_reservation_list", JSON.stringify(data))
    }
    list_reserv()
}

function filter_shedule(val) {
    if (val == "") {
        filt_shedule = null
    } else {
        filt_shedule = val
    }
    json_data = localStorage.getItem("diners_reservation_list")
    if (json_data) {
        data = JSON.parse(json_data)
        data.filt_shedule = filt_shedule
        data.sinc_page = 1
        localStorage.setItem("diners_reservation_list", JSON.stringify(data))
    } else {
        data = {
            sinc_page: 1,
            filt_confirmed: null,
            filt_shedule: filt_shedule,
            filt_diningroom: null,
            filt_date_gte: null,
            filt_date_lte: null
        }
        localStorage.setItem("diners_reservation_list", JSON.stringify(data))
    }
    list_reserv()
    select_link()
}

function filter_diningroom(val) {
    if (val == "") {
        filt_diningroom = null
    } else {
        filt_diningroom = val
    }
    json_data = localStorage.getItem("diners_reservation_list")
    if (json_data) {
        data = JSON.parse(json_data)
        data.filt_diningroom = filt_diningroom
        data.sinc_page = 1
        localStorage.setItem("diners_reservation_list", JSON.stringify(data))
    } else {
        data = {
            sinc_page: 1,
            filt_confirmed: null,
            filt_shedule: null,
            filt_diningroom: filt_diningroom,
            filt_date_gte: null,
            filt_date_lte: null
        }
        localStorage.setItem("diners_reservation_list", JSON.stringify(data))
    }
    list_reserv()
    select_link()
}


function list_html(dicc) {
    m_tbody = document.getElementById("body_table")
    m_tbody.innerHTML = ""
    for (let i = 0; i < dicc.reservs.length; i++) {
        tuple = ""
        tuple = tuple + "<tr id=\"reserv_" + dicc.reservs[i].id_rserv + "\">\n"
        if (dicc.action) {
            tuple = tuple + "<td class=\"action-checkbox\">\n" +
                "           <input type=\"checkbox\" name=\"_selected_action\" value=\"" + dicc.reservs[i].id_rserv + "\" class=\"action-select\">\n" +
                "       </td>\n"
        }
        tuple = tuple + "<th class=\"field-get_person_model\">\n" +
            "           <a href=\"/reservation/reservation/" + dicc.reservs[i].id_rserv + "/change/\" id=\"" + dicc.reservs[i].id_rserv + "_name\">\n" +
            "               " + dicc.reservs[i].person + "\n" +
            "           </a>\n" +
            "       </th>\n" +
            "       <td class=\"field-get_diningroom_model\" >\n" +
            "           <span class=\"person\" id=\"" + dicc.reservs[i].id_rserv + "_diningroom\">\n" +
            "               " + dicc.reservs[i].diningroom + "\n" +
            "           </span>\n" +
            "       </td>\n" +
            "       <td class=\"field-get_area_person_model\" id=\"" + dicc.reservs[i].id_rserv + "_area\">\n" +
            "           " + dicc.reservs[i].area + "\n" +
            "       </td>\n" +
            "       <td class=\"field-menu nowrap\">\n" +
            "           " + dicc.reservs[i].menu + "\n" +
            "       </td>\n" +
            "       <td class=\"field-is_confirmed\">\n" +
            dicc.reservs[i].is_confirmed +
            "       </td>\n" +
            "       <td class=\"field-more_actions\">\n" +
            dicc.reservs[i].more_action +
            "       </td>\n" +
            "   </tr>\n"
        m_tbody.innerHTML = m_tbody.innerHTML + tuple
    }
    sinc_paginator = document.getElementById("sinc_paginator")
    json_data = localStorage.getItem("diners_reservation_list")
    if (json_data) {
        data = JSON.parse(json_data)
        sinc_page = data.sinc_page

    } else {
        sinc_page = 1
    }
    limitinf = sinc_page - 3
    limitsup = sinc_page + 3
    if (limitinf < 1) {
        limitinf = 1
    }
    if (limitsup > dicc.pages) {
        limitsup = dicc.pages
    }
    html_paginator = ""
    if (1 < limitinf) {
        html_paginator = html_paginator + "<a href=\"#\" onclick=\"change_page(1)\">1</a>\n"
    }
    if (2 < limitinf) {
        html_paginator = html_paginator + "<a href=\"#\" onclick=\"change_page(1)\">2</a>\n"
    }
    if (html_paginator != "" && sinc_page != 4) {
        html_paginator = html_paginator + "...\n"
    }
    position = limitinf
    while (position <= limitsup) {
        if (sinc_page == position) {
            html_paginator = html_paginator + "<span class=\"this-page\">" + sinc_page + "</span>\n"
        } else {
            html_paginator = html_paginator + "<a "
            if (position == dicc.pages) {
                html_paginator = html_paginator + "class=\"end\" "
            }
            html_paginator = html_paginator + "href=\"#\" onclick=\"change_page(" + position + ")\">" + position + "</a>\n"
        }
        position++
    }
    html_final = ""
    if ((dicc.pages - 1) > limitsup) {
        html_final = html_final + "<a href=\"#\" onclick=\"change_page(" + (dicc.pages - 1) + ")\">" + (dicc.pages - 1) + "</a>\n"
    }
    if (dicc.pages > limitsup) {
        html_final = html_final + "<a class=\"endresult_list\" href=\"#\" onclick=\"change_page(" + dicc.pages + ")\">" + dicc.pages + "</a>\n"
    }
    if (html_final != "") {
        if (limitsup + 1 != dicc.pages - 1 && limitsup + 1 != dicc.pages) {
            html_paginator = html_paginator + "...\n"
        }
    }
    html_paginator = html_paginator + html_final + dicc.total + " reservaciones"
    sinc_paginator.innerHTML = html_paginator

    if (dicc.action) {
        counter = document.getElementsByClassName("action-counter")[0]
        text_list = counter.innerHTML.split(" ")
        counter.innerHTML = text_list[0] + " " + text_list[1] + " " + text_list[2] + " " + dicc.reservs.length
    }
}

async function list_reserv() {
    json_data = localStorage.getItem("diners_reservation_list")
    if (json_data) {
        data = JSON.parse(json_data)
    } else {
        data = {
            sinc_page: 1,
            filt_confirmed: null,
            filt_shedule: null,
            filt_diningroom: null,
            filt_search: null,
            filt_date_gte: null,
            filt_date_lte: null
        }
        localStorage.setItem("diners_reservation_list", JSON.stringify(data))
    }
    loader_paginator = document.getElementById("loader-paginator")
    if (loader_paginator) {
        loader_paginator.classList.remove("box_inv")
    }
    list_html(await connect_post_backend('/reservation/reservation/reservs_return/', {
        page: data.sinc_page,
        confirmed: data.filt_confirmed,
        shedule: data.filt_shedule,
        dinningroom: data.filt_diningroom,
        search: filt_search,
        date_gte: data.filt_date_gte,
        date_lte: data.filt_date_lte
    }))
    loader_paginator.classList.add("box_inv")
    init_checks_action()
    isAllSelected()
}

async function change_confirm(id_reserv) {
    check = document.getElementById("check_" + id_reserv)
    if (check.classList.contains("check")) {
        val = true
        check.classList.remove("check")
    } else {
        val = false
        check.classList.remove("uncheck")
    }
    check.classList.add("check_load")
    resp = (await connect_post_backend("/reservation/reservation/confirm_reservation/", {
        id: id_reserv
    }))
    if (resp.type == "success") {
        if (val) {
            val = false
        } else {
            val = true
        }
    }
    if (localStorage.getItem("camera_window") === "true") {
        manualConfirm(resp)
    }
    showMessage(resp.type, resp.mess)
    if (resp.person) {
        showMessage(resp.person.type, resp.person.mess)
    }
    check.classList.remove("check_load")
    if (val) {
        check.classList.add("check")
    } else {
        check.classList.add("uncheck")
    }
}

async function delete_reserv_modal(id_reserv) {
    resp = (await connect_get_backend("/reservation/reservation/delete_reservation/?reserv=" + id_reserv))
    if (resp.type == "error") {
        showMessage(resp.type, resp.mess)
    } else {
        info_head = "¿Está seguro?"
        body_html = "\n" +
            "       " + resp.pre_text + "<a href=\"/reservation/reservation/" + id_reserv + "/change/\">" + resp.reserv_text + "</a>\n" +
            "       " + resp.suf_text + "\n"
        modal = {"type": "yesornot", "func": {"yes": "delete_reserv(" + resp.id_reserv + ")"}}
        showModal(info_head, body_html, modal)
    }
}

async function delete_reserv(id_reserv) {
    resp = (await connect_post_backend("/reservation/reservation/delete_reservation/", {id: id_reserv}))
    showMessage(resp.type, resp.mess)
    if (resp.person) {
        showMessage(resp.person.type, resp.person.mess)
    }
    list_reserv()
    $.modal.close();
}

function focus_check(id) {
    check = check = document.getElementById("check_" + id)
    check.classList.toggle("focus")
}

function load_links_localstorage() {
    json_data = localStorage.getItem("diners_reservation_list")
    if (json_data) {
        data = JSON.parse(json_data)
        // filt_date - fecha
        ul_filt_date = document.getElementById("filt_date").children
        for (let e = 0; e < ul_filt_date.length; e++) {
            ul_filt_date[e].classList.remove("selected")
        }
        if (data.filt_date_gte == null && data.filt_date_lte == null) {
            ul_filt_date[0].classList.add("selected")
        } else {
            if (data.filt_date_gte != null) {
                ul_filt_date[2].classList.add("selected")
                document.getElementById('date_gte').value = data.filt_date_gte
            }
            if (data.filt_date_lte != null) {
                ul_filt_date[3].classList.add("selected")
                document.getElementById('date_lte').value = data.filt_date_lte
            }
        }
        // filt_confirmed - confirmado
        ul_filt_confirmed = document.getElementById("filt_confirmed").children
        for (let e = 0; e < ul_filt_confirmed.length; e++) {
            ul_filt_confirmed[e].classList.remove("selected")
            if (ul_filt_confirmed[e].dataset.value == data.filt_confirmed) {
                ul_filt_confirmed[e].classList.add("selected")
            }
        }
        if (data.filt_confirmed == null) {
            ul_filt_confirmed[0].classList.add("selected")
        }
        // filt_shedule - horario
        ul_filt_shedule = document.getElementById("filt_shedule").children
        for (let e = 0; e < ul_filt_shedule.length; e++) {
            ul_filt_shedule[e].classList.remove("selected")
            if (ul_filt_shedule[e].dataset.value == data.filt_shedule) {
                ul_filt_shedule[e].classList.add("selected")
            }
        }
        if (data.filt_shedule == null) {
            ul_filt_shedule[0].classList.add("selected")
        }
        // filt_diningroom - comedor
        ul_filt_diningroom = document.getElementById("filt_diningroom").children
        for (let e = 0; e < ul_filt_diningroom.length; e++) {
            ul_filt_diningroom[e].classList.remove("selected")
            if (ul_filt_diningroom[e].dataset.value == data.filt_diningroom) {
                ul_filt_diningroom[e].classList.add("selected")
            }
        }
        if (data.filt_diningroom == null) {
            ul_filt_diningroom[0].classList.add("selected")
        }
    }
}