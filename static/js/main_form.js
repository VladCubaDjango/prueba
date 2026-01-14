let diet;
const error_class = 'errors';
const delete_class = 'response_json';

window.addEventListener('load', init);
document.addEventListener("visibilitychange", () => {
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
    localStorage.setItem("camera_person", JSON.stringify({qr: qr_data_qr, windows: "reserv_reserv"}))
}

function init() {
    change_qr_windows()
    const menu = document.getElementById('id_menu');
    diet = document.getElementById('id_is_diet');
    const dishes = document.getElementById('id_dishes');
    const form = document.getElementById('reservation_form');
    const reset_button = document.getElementById("reset_button");

    function resetValues() {
        dismarkOptions(dishes);
        if (menu.disabled === false) {
            menu.selectedIndex = 0;
            cleanOptions(dishes);
        }
        disabled_submit(false);
        calculateAmount(dishes.selectedOptions);
    }

    if (dishes.dataset.disabled === "1") {
        let options = dishes.childNodes;
        options.forEach(function (element) {
            element.addEventListener("mousedown", function (e) {
                e.preventDefault();
                element.parentElement.focus();
                this.selected = !this.selected;
                calculateAmount(dishes.selectedOptions);
                return false;
            }, false);
        });
    }

    if (form.dataset.type_view === 'change') {
        document.getElementById('id_extra_data').value = form.dataset.extra_data;
        document.getElementById('id_extra_diet').value = form.dataset.is_diet;
        diet.checked = form.dataset.is_diet.toLowerCase() === 'true';
    }

    if (reset_button) {
        reset_button.addEventListener("click", e => {
            deleteAll();
//            deleteMessageList();
            if (document.getElementById("id_area").disabled === false) {
                resetField("id_area");
            }
            if (document.getElementById("id_person").disabled === false) {
                resetField("id_person");
            }
            +resetValues();
            window.scrollTo(0, 0);
        });
    }

    const calculateAmount = options => {
        let number = 0;
        for (let option of options) number += parseFloat(option.dataset.price);
        let price = `Importe: $${number.toFixed(2).replace(/(\d)(?=(\d\d\d)+(?!\d))/g, "$1,")}`;
        const fieldDishes = document.querySelector('.field-dishes');
        const strong = document.createElement('strong');
        strong.innerHTML = price;
        fieldDishes.removeChild(fieldDishes.lastChild);
        fieldDishes.appendChild(strong);
    };
    const loadDishes = (idMenu, dietChecked) => {
        fetch('/reservation/reservation/process-dishes/', {
            method: 'POST',
            headers: {'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken')},
            body: JSON.stringify({id: idMenu, is_diet: dietChecked}),
        })
            .then(response => response.text())
            .then(res => {
                dishes.innerHTML = res;
                calculateAmount(dishes.selectedOptions);
                print_dishes(document.getElementById("id_dishes"))
            });
    }
    calculateAmount(dishes.selectedOptions);

    menu.addEventListener('change', e => loadDishes(e.target.value, diet.checked));
    diet.addEventListener('change', e => loadDishes(menu.value, e.target.checked));
    dishes.addEventListener('change', e => calculateAmount(e.target.selectedOptions));
    form.addEventListener('submit', e => {
        e.preventDefault();
        const url = form.dataset.url;
        fetch(url, {
            method: 'POST',
            headers: {'X-CSRFToken': getCookie('csrftoken'), 'Accept': 'application/json'},
            body: new FormData(e.target),
        }).then(response => {
            deleteAll();
            let json = response.json();
            if (response.ok) {
                json.then(data => {

                    showMessage("success", data.log_message)


                    right_text = "Entregue la tarjeta por favor";
                    left_text = "RESERVADO";
                    footer = "¡Hasta Pronto!";
                    if (document.getElementById("reservation_form").dataset.type_view == "change") {
                        left_text = "EDITADO";
                        footer = "";
                    }

                    if (data.hasOwnProperty("pay_message")) {
                        showMessage(data.success_class, data.pay_message)
                        right_text = html_qr_footer(data.success_class, data.amount);
                    }

                    if (localStorage.getItem("camera_window") === "true") {
                        print_dishes(document.getElementById("id_dishes"))

                        local = localStorage.getItem("camera_info")
                        id_info_v = 0
                        local_info = {
                            id_info: 0,
                            name: "",
                            date: "",
                            body: "",
                            left_footer: "",
                            rigt_footer: "",
                            page_foot: ""
                        }
                        if (local != null) {
                            local_info = JSON.parse(local)
                            id_info_v = local_info.id_info + 1
                        }
                        local_info.rigt_footer = right_text
                        local_info.left_footer = left_text
                        local_info.page_foot = footer
                        local_info.id_info = id_info_v
                        localStorage.setItem("camera_info", JSON.stringify(local_info))
                    }

                    if (form.dataset.type_view === 'add') {
                        resetValues();
                    }

                    if (dishes.dataset.disabled === "1") {
                        dishes.disabled = true;
                        document.getElementById("id_is_confirmed").disabled = true;
                        document.getElementsByName("_continue")[0].remove();
                    }

                    window.scrollTo(0, 0);
                    document.getElementById('id_extra_data').value = data.extra_data;

                    const query = 'query getPerson($id: ID){personById(id: $id){name}}';
                    document.querySelectorAll(".success .reservation_person").forEach(function (e) {
                        //TODO cambiar el then de arriba para poder usar api_conection y await en este fetch
                        fetch("/reservation/reservation/api_identity/", {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                                'X-CSRFToken': getCookie("csrftoken")
                            },
                            body: JSON.stringify({query: query, variables: {id: e.innerHTML}}),
                        }).then(response => {
                            let json = response.json();
                            if (response.ok) {
                                json.then(result => e.innerHTML = result.data.personById.name);
                            }
                        });
                    });
                });
            } else {
                json.then(error => {
                    deleteAll();
                    let log_message = document.createElement("p");
                    log_message.classList.add("errornote", delete_class);
                    log_message.innerHTML = error.log_message;

                    let fieldset = document.getElementsByClassName("module aligned ")[0];
                    let div = fieldset.parentElement

                    const errors = error.errors;

                    for (let key in errors) {
                        if (errors.hasOwnProperty(key)) {
                            const value = errors[key]
                            if (key === "__all__") {
                                let li = document.createElement("li");
                                li.innerHTML = value;

                                if (localStorage.getItem("camera_window") === "true") {
                                    local = localStorage.getItem("camera_info")
                                    id_info_v = 0
                                    local_info = {
                                        id_info: 0,
                                        name: "",
                                        date: "",
                                        body: "",
                                        left_footer: "",
                                        rigt_footer: "",
                                        page_foot: ""
                                    }
                                    if (local != null) {
                                        local_info = JSON.parse(local)
                                        id_info_v = local_info.id_info + 1
                                    }
                                    local_info.body = html_qr_body_add("error", value)
                                    local_info.page_foot = ""
                                    local_info.id_info = id_info_v
                                    localStorage.setItem("camera_info", JSON.stringify(local_info))
                                }

                                let ul = document.createElement("ul");
                                ul.classList.add("errorlist", "nonfield", delete_class);
                                ul.appendChild(li);

                                div.prepend(ul);
                            } else {
                                let li = document.createElement("li");
                                li.innerHTML = value;

                                let ul = document.createElement("ul");
                                ul.classList.add("errorlist", delete_class);
                                ul.appendChild(li);

                                const div_class = "field-" + key;
                                let div = document.getElementsByClassName(div_class)[0];
                                div.classList.add(error_class);
                                div.prepend(ul);
                            }
                        }
                    }
                    div.prepend(log_message);
                    window.scrollTo(0, 0);
                });
            }
        }).catch(error => {
            deleteAll();
            let fieldset = document.getElementsByClassName("module aligned ")[0];
            let div = fieldset.parentElement

            let li = document.createElement("li");
            li.innerHTML = 'No hay conexión al sistema, intentelo nuevamente';

            let ul = document.createElement("ul");
            ul.classList.add("errorlist", "nonfield", delete_class);
            ul.appendChild(li);

            div.prepend(ul);
            window.scrollTo(0, 0);
        });
    });
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

function select_person(person) {
    const method = 'POST';
    const csrftoken = getCookie('csrftoken');
    const url = '/reservation/reservation/process-person/';

    const body = JSON.stringify({'id': person.id});

    fetch(url, {
        method: method,
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken
        },
        body: body,
    }).then(response => {
        deleteAll();
//        deleteMessageList();
        let json = response.json();
        if (response.ok) {
            json.then(result => {
                const option = new Option(result.text, result.id, true, true);
                $('#id_area').append(option).trigger('change');

                document.getElementById('id_extra_data').value = result.extra_data;
                document.getElementById('id_extra_diet').value = result.is_diet;

                if (localStorage.getItem("camera_window") === "true") {

                    local = localStorage.getItem("camera_info")
                    id_info_v = 0
                    local_info = {
                        id_info: 0,
                        name: "",
                        date: "",
                        body: "",
                        left_footer: "",
                        rigt_footer: "",
                        page_foot: ""
                    }
                    if (local != null) {
                        local_info = JSON.parse(local)
                        id_info_v = local_info.id_info + 1
                    }


                    extra_data = result.extra_data.split(',')
                    local_info.left_footer = ""
                    if (extra_data[1] == "AP") {
                        right_text = html_qr_footer(result.class_alert, extra_data[2]);
                        local_info.rigt_footer = right_text
                    } else {
                        local_info.rigt_footer = "Pago por tarjeta"
                    }
                    local_info.page_foot = ""
                    local_info.id_info = id_info_v
                    localStorage.setItem("camera_info", JSON.stringify(local_info))
                }

                disabled_submit(false);


                showMessage(result.class_alert, result.log_message)


                check_automatic_diet(result.is_diet);
            });
        } else {
            json.then(error => {

                disabled_submit(true);


                showMessage(error.class_alert, error.log_message)

            });
        }
    }).catch(error => {
        deleteAll();
        let fieldset = document.getElementsByClassName("module aligned ")[0];
        let div = fieldset.parentElement

        let li = document.createElement('li');
        li.innerHTML = 'No hay conexión al sistema, intentelo nuevamente';

        let ul = document.createElement('ul');
        ul.classList.add('errorlist', 'nonfield', delete_class);
        ul.appendChild(li);

        div.prepend(ul);
    });
}

function disabled_submit(disabled) {
    document.querySelectorAll('[type=submit]').forEach(e => e.disabled = disabled);
}

function dismarkOptions(selectElement) {
    let elements = selectElement.options;
    for (let i = 0; i < elements.length; i++) {
        elements[i].selected = false;
    }
}

const cleanOptions = selectElement => {
    while (selectElement.firstChild) {
        selectElement.removeChild(selectElement.firstChild);
    }
};

function deleteAll() {
    document.querySelectorAll("." + error_class).forEach(e => e.classList.remove(error_class));
    document.querySelectorAll("." + delete_class).forEach(e => e.remove());
}


function resetField(id) {
    let select = document.getElementById(id);
    select.innerHTML = '';

    let span_select2 = document.getElementsByClassName("select2")[0];
    span_select2.classList.remove("select2-container--below", "select2-container--focus");

    let span_select_person = document.getElementById("select2-" + id + "-container");
    span_select_person.removeAttribute('title')
    span_select_person.innerHTML = '<span class="select2-selection__placeholder"></span>';
}

function check_automatic_diet(checked) {
    diet.checked = checked;

    if ("createEvent" in document) {
        diet.dispatchEvent(new Event("change", {"bubbles": false, "cancelable": true}));
    } else {
        diet.fireEvent("onchange");
    }
}

function print_dishes(dishes) {
    local = localStorage.getItem("camera_info")
    id_info_v = 0
    local_info = {
        id_info: 0,
        name: "",
        date: "",
        body: "",
        left_footer: "",
        rigt_footer: "",
        page_foot: ""
    }
    if (local != null) {
        local_info = JSON.parse(local)
        id_info_v = local_info.id_info + 1
    }
    if (localStorage.getItem("camera_window") === "true" && dishes.length > 0) {
        if (document.getElementById("id_person").form.dataset.type_view == "change") {
            if (document.getElementById("id_person").form.dataset.extra_data.split(",")[1] == "CP") {
                local_info.rigt_footer = "Pago por tarjeta"
            }
        }
        local_info.body = html_qr_body_add("success", dishes.selectedOptions)
        local_info.page_foot = ""
        local_info.id_info = local_info.id_info + 1
        localStorage.setItem("camera_info", JSON.stringify(local_info))
    }
}

(function ($) {
    $(document).ready(function () {
        $('#id_area').on('select2:select', function (e) {
            deleteAll();
            $('#id_person').val(null).trigger('change');
        });

        $('#id_person').on('select2:select', function (e) {
            const data = e.params.data;
            const person = {'id': data.id};
            select_person(person);

        });
    });
    $(window).ready(function () {
        function first_change() {
            if (localStorage.getItem("camera_window") === "true" && document.getElementById("id_dishes").length > 0) {
                pay_text = "Pago por tarjeta"
                spliter = document.getElementById("id_person").form.dataset.extra_data.split(",")
                if (spliter[1] == "AP") {
                    pay_text = html_qr_footer(spliter[4], spliter[2])
                }

                local = localStorage.getItem("camera_info")
                id_info_v = 0
                local_info = {
                    id_info: 0,
                    name: "",
                    date: "",
                    body: "",
                    left_footer: "",
                    rigt_footer: "",
                    page_foot: ""
                }
                if (local != null) {
                    local_info = JSON.parse(local)
                    id_info_v = local_info.id_info + 1
                }
                local_info.rigt_footer = pay_text
                local_info.left_footer = ""
                local_info.id_info = id_info_v
                localStorage.setItem("camera_info", JSON.stringify(local_info))
                print_name(document.getElementById("id_person").selectedOptions[0].text)
                print_menu(document.getElementById("id_menu").selectedOptions[0])
                print_dishes(document.getElementById("id_dishes"))
            }
        }

        function print_name(name) {
            if (localStorage.getItem("camera_window") === "true") {
                local = localStorage.getItem("camera_info")
                id_info_v = 0
                local_info = {
                    id_info: 0,
                    name: "",
                    date: "",
                    body: "",
                    left_footer: "",
                    rigt_footer: "",
                    page_foot: ""
                }
                if (local != null) {
                    local_info = JSON.parse(local)
                    id_info_v = local_info.id_info + 1
                }
                local_info.name = name
                if (document.getElementById("id_menu").value == "") {
                    local_info.body = ""
                    local_info.date = ""
                }
                local_info.id_info = id_info_v
                localStorage.setItem("camera_info", JSON.stringify(local_info))
            }
        }

        function print_menu(menu) {
            if (localStorage.getItem("camera_window") === "true") {
                local = localStorage.getItem("camera_info")
                id_info_v = 0
                local_info = {
                    id_info: 0,
                    name: "",
                    date: "",
                    body: "",
                    left_footer: "",
                    rigt_footer: "",
                    page_foot: ""
                }
                if (local != null) {
                    local_info = JSON.parse(local)
                    id_info_v = local_info.id_info + 1
                }
                local_info.left_footer = ""
                local_info.page_foot = ""
                if (document.getElementById("id_extra_data").value.split(",")[1] == "CP") {
                    local_info.rigt_footer = "Pago por tarjeta"
                }
                if (menu.value != "") {
                    local_info.date = menu.text
                    body_html = html_qr_body_add("success", document.getElementById("id_dishes"))
                    local_info.body = body_html
                } else {
                    local_info.date = ""
                    body_html = html_qr_body_add("success", document.getElementById("id_dishes"))
                    local_info.body = ""
                }
                local_info.id_info = id_info_v
                localStorage.setItem("camera_info", JSON.stringify(local_info))
            }
        }


        $('#id_person').on('change', function (e) {
            if (e.target.selectedOptions[0]) {
                print_name(e.target.selectedOptions[0].text)

            }
        });
        $('#id_menu').on('change', function (e) {
            print_menu(e.target.selectedOptions[0])
        });
        $('#id_dishes').on('change', function (e) {
            print_dishes(e.target)
        });
        setTimeout(first_change, 800);
    });


})(jQuery);


function get_qr_person(person) {
    const option = new Option(person.name, person.id, true, true);
    $('#id_person').append(option).trigger('change');
    select_person(person);
}

local_qr = localStorage.getItem("camera_person")
var qr_reserv = null
if (local_qr != null) {
    qr_reserv = JSON.parse(local_qr).qr
}
window.addEventListener("load", to_reserv);

async function to_reserv() {
    while (true) {
        local = localStorage.getItem("camera_person")
        if (local != null) {
            local_qr = JSON.parse(local)
            if (local_qr.qr != qr_reserv) {
                qr_reserv = local_qr.qr
                if (local_qr.windows == "reserv_reserv") {
                    select_QR_person(qr_reserv)
                }
            }
        }
        await timeout(500);
    }
}

async function select_QR_person(code_qr) {
    const query_person = "id,name"
    const person = await getPersonFromCamera(query_person, code_qr);
    if (person.data != null) {
        get_qr_person(person.data)
        local = localStorage.getItem("camera_info")
        id_info_v = 0
        local_info = {
            id_info: 0,
            name: "",
            date: "",
            body: "",
            left_footer: "",
            rigt_footer: "",
            page_foot: ""
        }
        if (local != null) {
            local_info = JSON.parse(local)
            id_info_v = local_info.id_info + 1
        }
        local_info.name = person.data.name
        // local_info.rigt_footer = ""
        // local_info.left_footer = ""
        // local_info.page_foot = ""
        local_info.id_info = id_info_v
        localStorage.setItem("camera_info", JSON.stringify(local_info))
    }
}

function html_qr_body_add(type, data) {
    html_resp = "<div class=\"colmn-block\">"
    if (type == "success") {
        total = calculateAmount_float(data)
        for (var i = 0; i < data.length; i++) {
            option = data[i].text.split('-')
            dish = option[0]
            price = option[1]
            html_resp = html_resp + "<p>\n" +
                "                       <span class=\"elem-left\">" + dish + "</span>\n" +
                "                       <span class=\"elem-rigth\">" + price + "</span>\n" +
                "                    </p>"
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

function calculateAmount_float(options) {
    let number = 0;
    for (let option of options) number += parseFloat(option.dataset.price);
    return number;
}
