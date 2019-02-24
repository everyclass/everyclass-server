$(document).ready(function ($) {
    $(".row-clickable").click(function () {
        window.document.location = $(this).data("href");
    });
});

$(document).ready(function () {
    var ua = window.navigator.userAgent.toLowerCase();
    if (ua.match(/MicroMessenger/i) == 'micromessenger') {
        $("#wechat-browser-tip").css("display", "block");
        $("#wechat-notify").css("display", "block");

    }
});