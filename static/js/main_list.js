window.addEventListener('load', init);

async function init() {
    const table_list = document.getElementById('result_list');

    const breadcrumbs = document.getElementsByClassName('breadcrumbs');

    if (table_list) {
        const tBody = table_list.getElementsByTagName('tbody')[0];
        const tableRow = tBody.getElementsByTagName('tr');

        const query = 'query getPerson($id: ID){personById(id: $id){name,area{name}}}';
        for (let t = 0; t < tableRow.length; t++) {
            const id = tableRow[t].getElementsByClassName('field-get_area_person_model')[0].innerHTML;

            resp = (await connect_post_identity(query, {id: id}, false))
            const person = resp.data.personById
            tableRow[t].getElementsByClassName('field-get_person_model')[0].childNodes[0].innerHTML = person.name;
            tableRow[t].getElementsByClassName('field-get_area_person_model')[0].innerHTML = person.area.name;

            const dinning = tableRow[t].getElementsByClassName('field-get_diningroom_model')[0].childNodes[0];
            if (dinning.className === 'dining_room') {
                const query = 'query getDiningRoomByID($id: ID){diningRoomById(id: $id){name}}'

                resp = (await connect_post_identity(query, {id: dinning.innerHTML}, false))
                dinning.innerHTML = resp.data.diningRoomById.name

            } else if (dinning.className === 'person') {
                const query = 'query getDiningRoomByPersonID($id: ID){dinerById(id: $id){diningRoom{name}}}'
                resp = (await connect_post_identity(query, {id: dinning.innerHTML}, false))
                dinning.innerHTML = resp.data.dinerById.diningRoom.name
            }
        }
    }

    if (breadcrumbs && breadcrumbs.length > 0 && breadcrumbs[0].innerText.match('Reservación para')) {
        const string_list = breadcrumbs[0].innerHTML.trim().split(" ");
        if (string_list[string_list.length - 2] === "de") {
            const pos = string_list.length - 7
            const id = string_list[pos];
            const query = 'query getPerson($id: ID){personById(id: $id){name}}';
            resp = (await connect_post_identity(query, {id: id}, false))
            string_list[pos] = resp.data.personById.name
            breadcrumbs[0].innerHTML = string_list.join(" ");


        }
    }

    function getNodeByTextContent(regEx) {
        const all = document.getElementsByTagName("*");
        return Array.prototype.slice.call(all).filter(function (el) {
            return el.innerText.match(regEx);
        });
    }

    function replace(element, from, to) {
        if (element.childNodes.length) {
            element.childNodes.forEach(child => replace(child, from, to));
        } else {
            const cont = element.textContent;
            if (cont) element.textContent = cont.replace(from, to);
        }
    }

    //EG: all nodes where the text begins with 'Reservación para'
    let matchedNodes = getNodeByTextContent(/^Reservación para/i);
    for (let i = 0; i < matchedNodes.length; i++) {
        const textToChange = matchedNodes[i].innerHTML
        const id = textToChange.split(' ')[2];

        const query = 'query getPerson($id: ID){personById(id: $id){name}}';
        resp = (await connect_post_identity(query, {id: id}, false))
        const name = resp.data.personById.name;
        const new_name = textToChange.replace(id, name);
        replace(document.body, textToChange, new_name);

    }
}

(function ($) {
    async function get_donate_name(donate_id) {
        let text = donate_id;
        if (text !== 'No tiene') {
            const query = 'query getPerson($id: ID) {personById(id: $id) {name}}';
            const resp_json = (await connect_post_identity(query, {id: donate_id}, false))
            if (resp_json.errors) {
                text = resp_json.errors[0].message;
            } else {
                text = resp_json.data.personById.name;
            }
        }
        return text;
    }

    $(document).ready(function () {
        $('.info-button').click(async function (e) {
            console.log("Entro")
            // e.preventDefault();
            // const reserv_id = $(this).attr('data-id');
            // const parent = this.parentElement.parentElement;
            // const name = parent.childNodes[1].childNodes[0].textContent;
            // await reserv_info_modal(reserv_id, name);
        });


    });
})(jQuery);

async function more_info(e) {
    e.preventDefault();
    target = e.target
    const reserv_id = target.attributes["data-id"].value
    const parent = target.parentElement.parentElement;
    const name = parent.getElementsByClassName("field-get_person_model")[0].textContent
    await reserv_info_modal(reserv_id, name);
}

async function reserv_info_modal(reserv_id, person_name) {
    resp = (await connect_post_backend('/reservation/reservation/detail-reservation/', {'id': reserv_id}))
    modal_reservation_more_info(resp, person_name)
}

async function modal_reservation_more_info(info, name) {

    const fields = info['fields'];

    let res = '';
    for (let field in fields) {
        let value = '';
        if (field === 'Persona' || field === 'Person') {
            value = name;
        } else if (field === 'Donación' || field === 'Donate') {
            value = await get_donate_name(fields[field]);
        } else {
            value = fields[field];
        }

        res += `<div class="col-md-6">
                    <p>
                        <div><b>${field}: </b></div>
                        <div><p>${value}</p></div>
                    </p>
                </div>
`;
    }
    showModal("Detalles adicionales de la reservación", res, {type: "ok"})

    let offplan = document.getElementsByClassName('offplan_person')[0];
    let substring = 'personById';
    if (!offplan) {
        offplan = document.getElementsByClassName('offplan_area')[0];
        substring = 'areaById';
    }

    const query = `query getName($id: ID) {${substring}(id: $id) {name}}`;
    if (offplan) {
        const resp_json = (await connect_post_identity(query, {id: offplan.innerText}, false))
        if (resp_json.errors) {
            offplan.innerText = resp_json.errors[0].message;
        } else {
            offplan.innerText = resp_json.data[substring]['name'];
        }
    }
}

async function get_donate_name(donate_id) {
    let text = donate_id;
    if (text !== 'No tiene') {
        const query = 'query getPerson($id: ID) {personById(id: $id) {name}}';
        const resp_json = (await connect_post_identity(query, {id: donate_id}, false))
        if (resp_json.errors) {
            text = resp_json.errors[0].message;
        } else {
            text = resp_json.data.personById.name;
        }
    }
    return text;
}

function invited_offplan_submit(e) {
    e.preventDefault();
    target = e.target
    const reserv_id = target.attributes["data-id"].value
    inp = document.getElementById("inp_id_rserv")
    inp.value = reserv_id
    form_iop = document.getElementById("form_invite_offplan")
    form_iop.submit()
}

function offplan_submit(e) {
    e.preventDefault();
    target = e.target
    const reserv_id = target.attributes["data-id"].value
    inp = document.getElementById("off_id_rserv")
    inp.value = reserv_id
    form_iop = document.getElementById("form_offplan")
    form_iop.submit()
}

function donate_submit(e) {
    e.preventDefault();
    target = e.target
    const reserv_id = target.attributes["data-id"].value
    inp = document.getElementById("don_id_rserv")
    inp.value = reserv_id
    form_iop = document.getElementById("form_donate")
    form_iop.submit()
}