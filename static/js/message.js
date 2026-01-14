window.addEventListener("load", init_message);

toastr.options = {
  "closeButton": true,
  "debug": false,
  "newestOnTop": false,
  "progressBar": true,
  "positionClass": "toast-top-right",
  "preventDuplicates": true,
  "onclick": null,
  "showDuration": "300",
  "hideDuration": "1000",
  "timeOut": "5000",
  "extendedTimeOut": "2500",
  "showEasing": "swing",
  "hideEasing": "linear",
  "showMethod": "fadeIn",
  "hideMethod": "fadeOut"
}

function init_message(){
    div = document.getElementById("messageslist")
    console.log(div)
    if (div){
        mess = div.children
        for(i=0;i<mess.length;i++){
            showMessage(mess[i].dataset.type, mess[i].innerHTML)
        }
    }
}

function showMessage(type, mess) {
    switch (type){
        case "success": title_ms = "";break;
        case "warning": title_ms = "ADVERTENCIA";break;
        case "error": title_ms = "";break;
        case "info": title_ms = "INFORMACIÓN";break;
        default: title_ms = "";
    }

    toastr[type](mess, title_ms)
}

function showListMessages(lis) {
    for (i = 0; i < lis.length; i++) {
        showMessage(lis[i].type, lis[i].mess)
    }
}