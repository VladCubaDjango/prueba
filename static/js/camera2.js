window.addEventListener("beforeunload", init_camera);
window.addEventListener("load", init_info);
local = localStorage.getItem("camera_info")
var id_info = null
if (local != null) {
    id_info = JSON.parse(local).id_info
}

function init_camera() {
    localStorage.setItem("camera_window", false)
}

async function init_info() {
    while (true) {
        local = localStorage.getItem("camera_info")
        if (local != null) {
            local_v = JSON.parse(local)
            if (id_info != local_v.id_info) {
                if (local_v.id_info >= 100){
                    local_v.id_info = 0
                    localStorage.setItem("camera_info", JSON.stringify(local_v))
                }
                id_info = local_v.id_info
                change_info(local_v.name, local_v.date, local_v.body, local_v.left_footer, local_v.rigt_footer, local_v.page_foot)
            }
        }
        await timeout(500);
    }
}

function save_qr(content) {
    qr_data = localStorage.getItem("camera_person")

    if(qr_data!=null){
        qr_data_windows = JSON.parse(qr_data).windows
        qr_data_qr = JSON.parse(qr_data).qr
        if (JSON.parse(qr_data).qr != content){
            loander_info()
        }
    }else{
        loander_info()
        qr_data_windows = null
    }
    localStorage.setItem("camera_person", JSON.stringify({qr: content , windows: qr_data_windows}))
}

function timeout(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

function loander_info() {
    document.getElementById("id_loanding_info").classList.remove("box_inv")
    document.getElementById("id_info_cont").classList.add("box_inv")
    change_footer_page("")
}

function see_info() {
    document.getElementById("id_loanding_info").classList.add("box_inv")
    document.getElementById("id_info_cont").classList.remove("box_inv")
    document.getElementById("id_head_info").classList.remove("box_inv")
    document.getElementById("id_footer_info").classList.remove("box_inv")
}

function change_info(name, date, body, foot_l, foot_r, foot_p) {
    see_info();
    change_head(name, date)
    change_body(body)
    change_footer(foot_l, foot_r)
    change_footer_page(foot_p)
}

function change_head(name, date) {
    document.getElementById("person_name").innerHTML = name
    document.getElementById("date_text").innerHTML = date
}

function change_person_name(name) {
    see_info();
    document.getElementById("person_name").innerHTML = name
}

function change_date(date) {
    see_info();
    document.getElementById("date_text").innerHTML = date
}

function change_body(body) {
    see_info();
    document.getElementById("id_body_info").innerHTML = body
}

function change_footer(left_text, right_text) {
    see_info();
    document.getElementById("left-footer").innerHTML = left_text
    document.getElementById("right-footer").innerHTML = right_text
}

function change_footer_left_text(left_text) {
    document.getElementById("left-footer").innerHTML = left_text
}

function change_footer_right_text(right_text) {
    document.getElementById("right-footer").innerHTML = right_text
}

function change_footer_page(text) {
    document.getElementById("page_foot").innerHTML = text
}
