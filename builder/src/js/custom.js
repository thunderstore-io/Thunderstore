function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie != "") {
        var cookies = document.cookie.split(";");
        for (var i = 0; i < cookies.length; i++) {
            var cookie = cookies[i].trim();

            if (cookie.substring(0, name.length + 1) == name + "=") {
                cookieValue = decodeURIComponent(
                    cookie.substring(name.length + 1)
                );
                break;
            }
        }
    }
    return cookieValue;
}

// This is pretty horrible state management to be honest, but whatever
function ratePackage() {
    var $el = $(this);

    // Already syncing
    if ($el.hasClass("fa-sync")) {
        return;
    }

    var targetState = "rated";
    if ($el.hasClass("rated")) {
        targetState = "unrated";
    }

    var pkg = $el.data("target");
    var url = "/api/v1/package/" + pkg + "/rate/";
    var payload = JSON.stringify({ target_state: targetState });

    $.post(url, payload, function (response) {
        var $score = $("#package-rating-" + pkg);
        $score.text(response.score);
        if (response.state == "rated") {
            $el.addClass("rated");
        } else {
            $el.removeClass("rated");
        }
    }).always(function () {
        $el.addClass("fa-thumbs-up");
        $el.removeClass("fa-sync rotate");
    });

    $el.addClass("fa-sync rotate");
    $el.removeClass("fa-thumbs-up");
}

$(document).ready(function () {
    $.ajaxSetup({
        headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
            "X-CSRFToken": getCookie("csrftoken"),
        },
    });
    $.get("/api/v1/current-user/info/", function (response) {
        if (response.capabilities.includes("package.rate")) {
            var $ratingButtons = $('[data-action="package.rate"]');
            $ratingButtons.addClass("clickable");
            $ratingButtons.click(ratePackage);
        }
        for (var index in response.ratedPackages) {
            var id = response.ratedPackages[index];
            var sel = '[data-action="package.rate"][data-target="' + id + '"]';
            $(sel).addClass("rated");
        }
    });
});
