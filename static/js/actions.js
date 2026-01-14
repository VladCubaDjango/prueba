window.addEventListener("load", init_toggle_ckecks);

function init_toggle_ckecks() {
    check = document.getElementById("action-toggle")
    if (check) {
        check.addEventListener("click", function () {
            toggle_ckecks(check)
        })
    }
}

function init_checks_action() {
    checks = document.getElementsByClassName("action-select")
    for (i = 0; i < checks.length; i++) {
        checks[i].addEventListener("click", function () {
            selectRow(event, checks)
        })
    }
}

function toggle_ckecks(check) {
    checks = document.getElementsByClassName("action-select")
    if (check.checked) {
        for (r = 0; r < checks.length; r++) {
            checks[r].checked = true
            checks[r].parentElement.parentElement.classList.add("selected")
        }
        counter = document.getElementsByClassName("action-counter")[0]
        text_list = counter.innerHTML.split(" ")
        counter.innerHTML = text_list[0] + " " + checks.length + " " + text_list[2] + " " + checks.length
    } else {
        for (r = 0; r < checks.length; r++) {
            checks[r].checked = false
            checks[r].parentElement.parentElement.classList.remove("selected")
        }
        counter = document.getElementsByClassName("action-counter")[0]
        text_list = counter.innerHTML.split(" ")
        counter.innerHTML = text_list[0] + " " + "0" + " " + text_list[2] + " " + checks.length
    }
}

function selectRow(e, checks) {
    if (e.target.checked) {
        e.target.parentElement.parentElement.classList.add("selected")
    } else {
        e.target.parentElement.parentElement.classList.remove("selected")
    }
    counter = document.getElementsByClassName("action-counter")[0]
    text_list = counter.innerHTML.split(" ")
    cant_checked = 0
    for (i = 0; i < checks.length; i++) {
        if (checks[i].checked) {
            cant_checked++;
        }
    }
    counter.innerHTML = text_list[0] + " " + cant_checked + " " + text_list[2] + " " + checks.length
    isAllSelected()
}

function isAllSelected() {
    checks = document.getElementsByClassName("action-select")
    is_all_selected = true
    if (checks.length != 0) {
        for (q = 0; q < checks.length; q++) {
            if (!checks[q].checked) {
                is_all_selected = false
            }
        }
    } else {
        is_all_selected = false
    }
    document.getElementById("action-toggle").checked = is_all_selected
}

async function getAction() {
    ids = []
    checks = document.getElementsByClassName("action-select")
    for (q = 0; q < checks.length; q++) {
        if (checks[q].checked) {
            ids.push(checks[q].value)
        }
    }
    if (ids.length === 0) {
        showMessage("warning", "Se deben seleccionar elementos para poder realizar acciones sobre estos. No se han modificado elementos.")
    } else {
        action = document.getElementById("action-select-input").value
        if (action === "") {
            showMessage("warning", "No se seleccionó ninguna acción.")
        } else {
            resp = (await connect_get_backend("/reservation/reservation/action_reserv/?action=" + action + "&ids=" + ids))
            if (resp.type == "success") {
                showModal(resp.text_head, resp.body_html, resp.modal)
            } else {
                showMessage(resp.type, resp.mess)
            }
        }
    }
}

async function executeAction(ids) {
    action = document.getElementById("action-select-input").value
    if (action === "") {
        showMessage("warning", "No se seleccionó ninguna acción.")
    } else {
        corp = {ids: ids, action: action}
        resp = (await connect_post_backend("/reservation/reservation/action_reserv/", corp))
        showListMessages(resp.lis)
    }
    $.modal.close()
    list_reserv()
}
