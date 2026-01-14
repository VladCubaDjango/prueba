window.addEventListener("load", init_modal);

function init_modal() {
    container = document.getElementById("container").parentElement
    div = document.createElement("div")
    div.id = "generic_modal"
    div.class = "modal"
    container.appendChild(div)
    div = document.getElementById("generic_modal")
    div.innerHTML = "" +
        "<h1 id='modal_head'></h1>" +
        "<div id='modal_body'></div>" +
        "<div id='modal_controls'></div>"
}

function showModalYesOrNo(info_head, body_html, modal) {
    document.getElementById("modal_head").innerHTML = info_head
    document.getElementById("modal_body").innerHTML = body_html
    controls = document.getElementById("modal_controls")
    controls.innerHTML = "" +
        "   <div class='modal_control'>\n" +
        "       <input type=\"button\" onclick='" + modal.func.yes + "' value=\"Si, estoy seguro\">\n" +
        "       <input type=\"button\" onclick='$.modal.close();' class=\"button cancel-link\" value=\"No, llévame atrás\">\n" +
        "   </div>\n"
    $('#generic_modal').modal();
}

function showModalSaveOrCancel(info_head, body_html, modal) {
    document.getElementById("modal_head").innerHTML = info_head
    document.getElementById("modal_body").innerHTML = body_html
    controls = document.getElementById("modal_controls")
    controls.innerHTML = "" +
        "   <div class='modal_control'>\n" +
        "       <input type=\"button\" onclick='" + modal.func.save + "' value=\"Guardar\">\n" +
        "       <input type=\"button\" onclick='$.modal.close();' class=\"button cancel-link\" value=\"Cancelar\">\n" +
        "   </div>\n"
    $('#generic_modal').modal();
}

function showModalOk(info_head, body_html) {
    document.getElementById("modal_head").innerHTML = info_head
    document.getElementById("modal_body").innerHTML = body_html
    controls = document.getElementById("modal_controls")
    controls.innerHTML = "" +
        "   <div class='modal_control' align='center'>\n" +
        "       <input type=\"button\" onclick='$.modal.close();' class=\"button cancel-link\" value=\"OK\">\n" +
        "   </div>\n"
    $('#generic_modal').modal();
}

function showModal(info_head, body_html, modal) {
    switch (modal.type) {
        case "yesornot":
            showModalYesOrNo(info_head, body_html, modal);
            break;
        case "saveorcancel":
            showModalSaveOrCancel(info_head, body_html, modal);
            break;
        case "ok":
            showModalOk(info_head, body_html)
    }
}