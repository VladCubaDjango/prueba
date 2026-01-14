window.addEventListener('load', init);

function init() {
    let options = document.querySelectorAll("option");
    options.forEach(function (element) {
        element.addEventListener("mousedown", function (e) {
            e.preventDefault();
            element.parentElement.focus();
            this.selected = !this.selected;
            return false;
        }, false);
    });
}
