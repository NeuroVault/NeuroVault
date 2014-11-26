var params = [];
params["worldSpace"] = true;
params["expandable"] = true;
params["images"] = ["http://{{ request.get_host }}/media/images/1/MNI152.nii.gz",
                    "http://{{ request.get_host }}{{ image.file.url }}"];
params["luts"] = [{"name":"PuBu", "data":[[0,1,0.968627,0.984314],[0.125,0.92549,0.905882,0.94902],[0.25,0.815686,0.819608,0.901961],[0.375,0.65098,0.741176,0.858824],[0.5,0.454902,0.662745,0.811765],[0.625,0.211765,0.564706,0.752941],[0.75,0.0196078,0.439216,0.690196],[0.875,0.0156863,0.352941,0.552941],[1,0.00784314,0.219608,0.345098]]},
{"name":"OrRd", "data":[[0,1,0.968627,0.92549],[0.125,0.996078,0.909804,0.784314],[0.25,0.992157,0.831373,0.619608],[0.375,0.992157,0.733333,0.517647],[0.5,0.988235,0.552941,0.34902],[0.625,0.937255,0.396078,0.282353],[0.75,0.843137,0.188235,0.121569],[0.875,0.701961,0,0],[1,0.498039,0,0]]}];

var filename = "{{ request.get_host }}{{ image.file.url }}".replace(/^.*[\\\/]/, '')
params[filename] = {"parametric": true,  "lut":"OrRd", "negative_lut":"PuBu", "alpha":"0.75"};

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

    loadScript("http://{{ request.get_host }}/static/scripts/papaya.js", function () {
    loadScript("http://{{ request.get_host }}/static/scripts/jquery-1.10.2.min.js", function () {
    loadScript("http://{{ request.get_host }}/static/scripts/bootstrap.min.js", function () {

        $('#NeuroVaultPapayaHolder').addClass('nv-papaya-holder well');
        $('#NeuroVaultPapayaHolder').prepend($("<div class='papaya papaya-embedded' data-params='params'></div>"));
        $('#NeuroVaultPapayaHolder').prepend($('<h3>NeuroVault Image: <a href="http://localhost:8001/{{ image.url }}">{{image.name}}</a></h3>'));

        $('head').append($('<link rel="stylesheet" type="text/css" />').attr('href','http://{{ request.get_host }}/static/css/papaya.css'));
        $('head').append($('<link rel="stylesheet" type="text/css" />').attr('href','http://{{ request.get_host }}/static/css/bootstrap.css'));

        $('head').append($('<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no"/>'));
        $('head').append($('<meta name="apple-mobile-web-app-capable" content="yes">'))
        $('head').append($('<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">'))

    });
    });
    });
})();
