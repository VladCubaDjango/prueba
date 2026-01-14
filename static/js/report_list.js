window.addEventListener('load', init);

async function init() {
    const ul = document.getElementsByClassName('not-confirmed');

    if (ul) {
        const query = 'query getPerson($id: ID){personById(id: $id){name,area{name}}}';
        for (let z = 0; z < ul.length; z++) {
            const li = ul[z].getElementsByTagName('li');
            for (let t = 0; t < li.length; t++) {
                let span = li[t].firstChild.innerHTML;
                if (!isNaN(span)) {
                    resp = (await connect_post_identity(query, {id: span}, false))
                    person = resp.data.personById
                    if (person) {
                        li[t].firstChild.innerHTML = "<strong>" + person.name + "</strong> - " + person.area.name;
                    }
                } else {
                    li[t].firstChild.innerHTML = "<strong>" + span + "</strong>";
                }
            }
        }
    }

    const li_person = document.getElementsByClassName('offplan_person');
    const li_area = document.getElementsByClassName('offplan_area');

    if (li_person) {
        const query = 'query getPerson($id: ID){personById(id: $id){name,area{name}}}';
        for (let z = 0; z < li_person.length; z++) {
            const id = li_person[z].innerHTML;
            resp = (await connect_post_identity(query, {id: id}, false))
            li_person[z].innerHTML = "<strong>" + resp.data.personById.name + "</strong> - " + resp.data.personById.area.name;
        }
    }

    if (li_area) {
        const query = 'query getArea($id: ID){areaById(id: $id){name}}';
        for (let z = 0; z < li_area.length; z++) {
            const id = li_area[z].innerHTML;
            resp = (await connect_post_identity(query, {id: id}, false))
            li_area[z].innerHTML = "<strong>Externo</strong> - " + resp.data.areaById.name;

        }
    }

    const invites = document.getElementsByClassName('invites');
    if (invites) {
        const query = 'query getPerson($id: ID){personById(id: $id){name}}';
        const query_area = 'query getArea($id: ID){areaById(id: $id){name}}';
        for (let z = 0; z < invites.length; z++) {
            const li = invites[z].getElementsByTagName('li');
            for (let t = 0; t < li.length; t++) {
                const element = li[t].firstChild;
                let id = element.innerHTML;
                let message;
                if (element.dataset.key === 'offplan_area') {
                    fetch_area = (await connect_post_identity(query_area, {id: id}, false))
                    message = fetch_area.data.areaById.name;
                } else {
                    fetch_id = (await connect_post_identity(query, {id: id}, false))
                    message = fetch_id.data.personById.name;
                }

                element.innerHTML = "<strong>" + element.dataset.invite + "</strong> - " + message;
            }
        }
    }
}