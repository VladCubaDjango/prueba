function open_windows() {
    qr_window = window.open("/reservation/reservation/camera_qr/", "camera", "");
    qr_window.focus()
    localStorage.setItem("camera_window", true)
}


async function getPersonFromCamera(query_person, code_qr) {
    let resp = null;
    while (resp == null) {
        query = 'query{personByIdNumber(idNumber: "' + code_qr + '"){' + query_person + '}}'
        response = await connect_post_identity(query, {}, true)
        if (response) {
            const res = response
            if (res.errors) {
                for (let i = 0; i < res.errors.length; i++) {
                    showMessage_QR_error(res.errors[i].message);
                }
                resp = {"data": null};
            } else {
                resp = {"data": res.data.personByIdNumber};
            }
        } else {
            showMessage_QR_error("Problema con la conexión. Contacte al Administrador. Persona");
            await timeout(5000);
        }
    }
    return resp;
}

function showMessage_QR_error(mess) {
    showMessage("error", mess);
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
    local_info.date = ""
    local_info.body = "<div class=\"colmn-block body_error\"><p align=\"center\">" + mess + "</p></div>"
    local_info.left_footer = ""
    local_info.rigt_footer = ""
    local_info.page_foot = ""
    local_info.id_info = id_info_v
    localStorage.setItem("camera_info", JSON.stringify(local_info))
}

function timeout(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}