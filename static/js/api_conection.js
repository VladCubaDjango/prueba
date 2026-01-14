bandera = true
window.addEventListener("beforeunload", cahnge_bandera);

function cahnge_bandera() {
    bandera = false
}

function timeout(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

async function connect_post_backend(url, body) {
    let resp_json = null;
    while (resp_json == null) {
        const res = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie("csrftoken")
            },
            body: JSON.stringify(body)
        }).catch(error => console.log(error));
        if (res) {
            if (res.ok) {
                resp_json = (await res.json())
                return resp_json;
            } else {
                showMessage("error", "Error interno en el Servidor Comensales. Contacte al Administrador")
                await timeout(5000);
            }
        } else {
            if (bandera) {
                showMessage("error", "Problema con la conexión con el Sistema Comensales. Contacte al Administrador.")
            }
            await timeout(5000);
        }
    }
}

async function connect_get_backend(url) {
    let resp_json = null;
    while (resp_json == null) {
        const res = await fetch(url, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        }).catch(error => console.log(error));
        if (res) {
            if (res.ok) {
                resp_json = (await res.json())
                return resp_json;
            } else {
                showMessage("error", "Error interno en el Servidor Comensales. Contacte al Administrador")
                await timeout(5000);
            }
        } else {
            if (bandera) {
                showMessage("error", "Problema con la conexión con el Sistema Comensales. Contacte al Administrador.")
            }
            await timeout(5000);
        }
        resp_json = " "
    }
}

async function connect_post_identity(query, variables, token) {
    let resp_json = null;
    while (resp_json == null) {
        const res = await fetch("/reservation/reservation/api_identity/", {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie("csrftoken")
            },
            body: JSON.stringify({query: query, variables: variables, token: token}),
        }).catch(error => console.log(error));
        if (res) {
            if (res.ok) {
                resp_json = (await res.json())
                return resp_json;
            } else {
                showMessage("error", "Error interno en el Servidor de Identidad. Contacte al Administrador")
                await timeout(5000);
            }
        } else {
            if (bandera) {
                showMessage("error", "Problema con la conexión con el Sistema de Identidad. Contacte al Administrador.")
            }
            await timeout(5000);
        }
    }
}




