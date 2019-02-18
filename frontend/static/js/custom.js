$(document).ready(function ($) {
    $(".row-clickable").click(function () {
        window.document.location = $(this).data("href");
    });
});