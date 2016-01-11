{% load static from staticfiles %}
(function () {
    function loadScript(url, callback) {
    var script = document.createElement("script")
    script.type = "text/javascript";
    if (script.readyState) { //IE
        script.onreadystatechange = function () {
        if (script.readyState == "loaded" || script.readyState == "complete") {
            script.onreadystatechange = null;
            callback();
        }
    };
    } else { //Others
        script.onload = function () {
            callback();
        };
    }
    script.src = url;
    document.getElementsByTagName("head")[0].appendChild(script);
    }

    loadScript("http://{{ request.get_host }}{% static 'scripts/jquery-1.10.2.min.js'%}", function () {
        frame_src = "http://{{ request.get_host }}{% url 'papaya_iframe_embed' image.pk %}"
        $('#NeuroVaultPapayaHolder').prepend($("<iframe scrolling='no' frameborder='1' allowtransparency='true' id='NeuroVaultEmbedded' src='"+frame_src+"' />"));
        $('#NeuroVaultEmbedded').css({
            'width':'540px',
            'height':'540px',
            'backgroundColor':'transparent',
            'overflow':'hidden',
            'border':'0px'
        });
    });
})();
