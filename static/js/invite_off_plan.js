const error_class = "errors";
const delete_class = "response_json";
const message_list = "messagelist";

function deleteAll() {
    document.querySelectorAll("." + error_class).forEach(e => e.classList.remove(error_class));
    document.querySelectorAll("." + delete_class).forEach(e => e.remove());
}

function deleteMessageList() {
    document.querySelectorAll("." + message_list).forEach(e => e.remove());
}


(function ($) {
    $(document).ready(async function () {

        let form = document.getElementById("invite_off_plan_form");

        const query = 'query getPerson($id: ID){personById(id: $id){name}}';
        for (const e of document.querySelectorAll(".reservation_person")) {
            resp = (await connect_post_identity(query, {id: e.innerHTML}, false))
            e.innerHTML = resp.data.personById.name
        }

        $('#id_area').on('select2:select', () => {
            deleteAll();
        });

        $('#id_person').on('select2:select', function (e) {
            const data = e.params.data;
            const person = {'id': data.id};
            select_person(person);
        });

        $('#id_person').on('select2:unselect', function (e) {
            const data = e.params.data;

            const all_selected = Array.from(document.getElementsByClassName("select2-selection__choice"));
            if (!all_selected.some(e => e.title === data.text)) {
                document.querySelector(".id_" + data.id).remove();
                document.querySelector('#id_person option[value="' + data.id + '"]').remove();
                deleteAll();
            }
        });

        $('input:radio[name="ubication"]').change(e => {
            deleteAll();
            document.querySelectorAll('.diner_info').forEach(e => e.remove());
            $('#id_area').val(null).trigger('change');
            $('#id_person').val(null).trigger('change');
            if (e.target.value === '1') {
                $('.field-person').show();
            } else {
                $('.field-person').hide();
            }
        });

        form.addEventListener("submit", e => {
            e.preventDefault();
            const csrftoken = getCookie("csrftoken");
            const url = window.location.pathname + window.location.search;
            const data = new FormData(form);

            const div = document.createElement('div');
            div.id = 'offplan_modal';
            div.classList.add('modal');
            div.innerHTML = `<div style="text-align: center;" class="loader-container">
                                    <div class="loader"></div>
                                    <div class="loader2"></div>
                             </div>
                             <h1 align="center">Procesando reservaciones, por favor espere...</h1>`;

            const container = document.getElementById('container');
            container.appendChild(div);

            $('#offplan_modal').modal({
                escapeClose: false,
                clickClose: false,
                showClose: false,
            });

            fetch(url, {
                method: "POST",
                headers: {'X-CSRFToken': csrftoken},
                body: data,
            }).then(response => {
                deleteAll();
                const json = response.json();
                if (response.ok) {
                    json.then(result => {
                        window.location = result.path;
                    });
                } else {
                    json.then(error => {
                        $.modal.close();
                        document.getElementById('offplan_modal').remove();

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
                    });
                }
            }).catch(error => {
                $.modal.close();
                document.getElementById('offplan_modal').remove();

                deleteAll();
                let fieldset = document.getElementsByClassName("module aligned ")[0];
                let div = fieldset.parentElement

                let li = document.createElement("li");
                li.innerHTML = 'No hay conexión al sistema, intentelo nuevamente';

                let ul = document.createElement("ul");
                ul.classList.add("errorlist", "nonfield", delete_class);
                ul.appendChild(li);

                div.prepend(ul);
            });
        });

        function select_person(person) {
            const url = '/reservation/reservation/process-person/';

            fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie("csrftoken")
                },
                body: JSON.stringify({'id': person.id}),
            }).then(response => {
                let json = response.json();
                if (response.ok) {
                    json.then(result => {
                        let log_message = document.createElement("li");
                        log_message.classList.add(result.class_alert, 'diner_info', "id_" + person.id);
                        log_message.innerHTML = result.log_message;

                        let ul = document.getElementsByClassName(message_list)[0];
                        ul.appendChild(log_message);
                    });
                } else {
                    json.then(error => {
                        let log_message = document.createElement("li");
                        log_message.classList.add(error.class_alert, "id_" + person.id);
                        log_message.innerHTML = error.log_message;

                        let ul = document.getElementsByClassName(message_list)[0];
                        ul.appendChild(log_message);
                    });
                }
            }).catch(error => {
                let fieldset = document.getElementsByClassName("module aligned ")[0];
                let div = fieldset.parentElement

                let li = document.createElement("li");
                li.innerHTML = 'No hay conexión al sistema, intentelo nuevamente';

                let ul = document.createElement("ul");
                ul.classList.add("errorlist", "nonfield", delete_class);
                ul.appendChild(li);

                div.prepend(ul);
            });
            deleteAll();
        }
    });
})(jQuery);