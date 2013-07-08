//<![CDATA[
hs.registerOverlay({
	html: '<div class="closebutton" onclick="return hs.close(this)" title="Close"></div>',
	position: 'top right',
	fade: 2 // fading the semi-transparent overlay looks bad in IE
});

hs.graphicsDir = '/func/highslide/graphics/';
hs.outlineType      = 'rounded-white';
hs.wrapperClassName = 'draggable-header';
//hs.wrapperClassName = 'floating-caption';
hs.dimmingOpacity = 0;
hs.headingText = '<img src="/func/clogo.png" alt="MotoFortuna">';
hs.showCredits = false;
//]]>

var mfText = "Интернет-магазин &laquo;МотоФортуна&raquo;, тел. (044) 222-98-39";
var hsHTMLTitle = '<span style="vertical-align: top; padding-left: 5px; font-weight: normal; color: gray;">' + mfText + '</span>';
  

SRAX.Default.NO_HISTORY = true;
SRAX.Default.HAX_ANTICACHE = true;

function load_ajax(sender, callback) {
    return hs.htmlExpand(sender);
    if (callback) {
        hs.Expander.prototype.onAfterClose = function (sender) {
            var res = gethax(callback);
            hs.Expander.prototype.onAfterClose = undefined;
            return res;
        }
    }
}

function gethax(p) {
    // 1 - CONST Default URL
    // 2 - CONST Ajax TREE
    // 3 - CONST Last ID
    // 4 - VAR Defined Params
    return gethaxin(ajax_url, ajax_tree, ajax_lastid, p);
};

function gethaxin(url, atree, alastid, p) {
    var params = [];
    var haxparams = {
         'method': 'post',
         'id': 'ilist',
         'url': url,
         'form': 'dom'
    };
    var fx = SRAX.Fx;
    var haxfunc = function() {hax(haxparams)};
    var re = /^\d+$/i;

    if ('url' in p) {
        haxparams.url = p.url;
    }
    params.push('ajax_tree=' + atree);
    params.push('ajax_lastid=' + alastid);

    if ('form' in p) {
        haxparams.form = p.form;
    }

    if ('idcont' in p) {
        haxparams.id = p.idcont;
    }


    if ('id' in p) {
        if (!re.test(p.id)) {
            p.id = findid(p.id);
        }
        params.push('ajax_id=' + p.id);
    }

    if ('params' in p ) {
        params.push(p['params']);
    }

    haxparams.params = params.join('&');

    if ('fx' in p) {
        var myid = 'i' + p.id;
        fx.opacity(myid, {start:1, end:0, duration:0.2, callback:haxfunc})
        haxparams.onload = function() {fx.opacity(myid, {start:0, end:1, d:0.2})};
    } else {
        haxfunc();
    }
};

function findid(dest) {
    var t = ajax_tree.split('-');
    while (t.length) {
        pid    = t.pop();
        id     = parseInt(t.pop());
        marker = t.pop();
        if (marker == dest) {
            return id;
        }

    }
};

function obj(id) {
    return document.getElementById(id);
}

function load_html (sender, src, event, callback) {
    if (event) {
        hs.Expander.prototype[event] = function (sender) {
            var res = callback(sender);
            hs.Expander.prototype[event] = undefined;
            return res;
        }
    }

    params = {
        'headingText': hs.headingText + hsHTMLTitle,
        'outlineType': 'rounded-white',
        'dimmingOpacity': 0.2,
        'minWidth': 440,
        'align': 'center',
        'outlineType': 'rounded-white'
    }
    if (src) {
        params['src'] = src;
        params['objectType'] = 'ajax';
        params['minWidth'] = 700;
    }

    return hs.htmlExpand(sender, params);
};

function load_gallery(sender) {
    hs.align = 'center';
    hs.transitions = ['expand', 'crossfade'];
    hs.fadeInOut = true;
    hs.captionEval = 'this.a.title';
    hs.numberPosition = 'caption';
    hs.useBox = true;
    hs.width = 500;
    hs.height = 600;

    // Add the controlbar
    if (hs.addSlideshow) hs.addSlideshow({
        //slideshowGroup: 'group1',
        interval: 5000,
        repeat: false,
        useControls: true,
        fixedControls: 'fit',
        overlayOptions: {
            opacity: .75,
            position: 'bottom center',
            hideOnMouseOut: true
        }
    });
    return hs.expand(sender);
};

function hide_hint() {
    obj('hint').style.display = 'none';
    obj('query').focus();
}