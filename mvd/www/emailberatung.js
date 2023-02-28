function new_onlineberatung() {
    if (localStorage.getItem('anfage_gesendet') == '0') {
        var failed_validations = check_mandatory();
        if (failed_validations.length < 1) {
            localStorage.setItem('anfage_gesendet', '1');
            var kwargs = {
                'mv_mitgliedschaft': document.getElementById("mitgliedschaft_id").value,
                'telefon': document.getElementById("telefon").value,
                'email': document.getElementById("email").value,
                'anderes_mietobjekt': document.getElementById("anderes_mietobjekt").value,
                'frage': document.getElementById("frage").value,
                'datum_mietzinsanzeige': document.getElementById("datum_mietzinsanzeige").value
            }
            frappe.call({
                'method': 'mvd.www.emailberatung.new_beratung',
                'args': {
                    kwargs
                },
                'async': true,
                'callback': function(res) {
                    var beratung = res.message;
                    if (beratung != 'error') {
                        get_upload_keys(beratung);
                    }
                }
            });
        } else {
            alert("Bitte füllen Sie alle Pflichtfelder aus.");
        }
    } else {
        alert("Bitte warten, Ihre Anfrage wird bereits verarbeitet.");
    }
}

function check_mandatory() {
    mandatory_fields = [
        'telefon',
        'email',
        'frage'
    ]
    
    if (localStorage.getItem('mz_anfrage') == '1') {
        mandatory_fields.push('datum_mietzinsanzeige');
    }
    
    failed_validations = []
    
    for (var i=0; i < mandatory_fields.length; i++) {
        if (!$("#" + mandatory_fields[i]).val()) {
            failed_validations.push(mandatory_fields[i]);
            $("#" + mandatory_fields[i]).css("border", "1px solid red");
        } else {
            $("#" + mandatory_fields[i]).css("border", "1px solid #ccc");
        }
    }
    
    return failed_validations
}

$(':file').on('change',function(){
    var myFile = $(this).val();
    var upld = myFile.split('.').pop();
    var file_element = this;
    if(!["pdf", "jpg", "jpeg", "zip"].includes(upld)){
        alert("Nur Dateien vom Typ PDF und JPEG/JPG sind erlaubt.");
        $(file_element).val("");
    } else {
        // get legacy mode
        var kwargs = {
            'mv_mitgliedschaft': document.getElementById("mitgliedschaft_id").value
        }
        frappe.call({
            'method': 'mvd.www.emailberatung.check_legacy_mode',
            'args': {
                kwargs
            },
            'async': true,
            'callback': function(res) {
                var legacy_mode = res.message;
                if (legacy_mode) {
                    if(file_element.files[0].size > 3145728){
                       alert("Die Maximale Filegrösse beträgt 3MB.");
                       $(file_element).val("");
                    };
                } else {
                    if(file_element.files[0].size > 10485760){
                       alert("Die Maximale Filegrösse beträgt 10MB.");
                       $(file_element).val("");
                    };
                }
            }
        });
    }
})

function add_new_file_row() {
    var new_id = $(':file').length + 1;
    if (new_id <= 15) {
        var klon = $("#default_file_row").clone(true);
        klon[0].id = "file_row_" + String(new_id);
        $(klon[0].children[0].children[0].children[0]).text('Zusätzliche Datei');
        klon[0].children[0].children[0].children[1].id = "upload_files_" + String(new_id);
        klon[0].children[1].children[0].children[1].id = "upload_files_dateupload_files_date_" + String(new_id);
        klon[0].children[2].children[1].children[0].id = "upload_files_auswahl_" + String(new_id);
        
        
        if ($(':file').length != 1) {
            $("#" + "file_row_" + String($(':file').length)).after(klon);
        } else {
            $("#default_file_row").after(klon);
        }
        init_awesomplete("upload_files_auswahl_" + String(new_id));
        $("#upload_files_auswahl_" + String(new_id)).attr('readonly', false);
        setTimeout(function(){
            $(".awesomplete-delete").each(function(){
                $(this).off('click');
                $(this).empty();
                if (!$(this).prev().prev().prev().attr('readonly')&&$(this).prev().prev().prev().children('input').length < 1) {
                    $(this).html('<i class="fa fa-xmark"></i>');
                    $(this).click(function(){
                        $(this).prev().prev().prev().val('');
                    });
                } else if (!$(this).prev().prev().prev().children('input').attr('readonly')&&$(this).prev().prev().prev().children('input').length > 0) {
                    $(this).prev().prev().prev().children('input').val('');
                }
            });
        }, 1000);
        $("#upload_files_auswahl_" + String(new_id)).val('');
    } else {
        alert("Die Maximale Anzahl Files beträgt 15.");
    }
}

function get_upload_keys(beratung) {
    if (beratung) {
        frappe.call({
            method: 'mvd.www.emailberatung.get_upload_keys',
            callback: function(res) {
                upload_files(beratung, res.message.key, res.message.secret, loop=1);
            }
        });
    }
}

function upload_files(beratung, key, secret, loop=1) {
    if (loop <= $(':file').length) {
        if ($("#upload_files_" + String(loop))[0].files[0]) {
            var file_name = '';
            if ($("#upload_files_dateupload_files_date_" + String(loop)).val()) {
                var document_date = $("#upload_files_dateupload_files_date_" + String(loop)).val().replace("-", "_").replace("-", "_")
                file_name += document_date + "_";
            } else {
                var document_date = '';
            }
            if ($("#upload_files_auswahl_" + String(loop)).val()) {
                var document_type = $("#upload_files_auswahl_" + String(loop)).val()
                if (['Mietvertrag', 'Mietzinserhöhung', 'Mietzinsherabsetzung', 'Vergleich/Urteil', 'Vereinbarung', 'sonstige Vertragsänderung'].includes(document_type)) {
                    file_name += document_type.replace("/", "_").replace(" ", "_") + "_";
                } else {
                    file_name += 'Sonstiges_';
                }
            } else {
                var document_type = '';
            }
            file_name += document.getElementById("mitgliedschaft_nr").value + "_" + String(loop) + "." + $(':file')[loop - 1].value.split('.').pop();
            
            let upload_file = new FormData();
            upload_file.append('file', $("#upload_files_" + String(loop))[0].files[0], file_name);
            upload_file.append('is_private', 1);
            upload_file.append('doctype', 'Beratung');
            upload_file.append('docname', beratung);
            fetch('/api/method/upload_file', {
                headers: {
                    'Authorization': 'token ' + key + ':' + secret
                },
                method: 'POST',
                body: upload_file
            }).then(function(res){
                var kwargs = {
                    'beratung': beratung,
                    'idx': loop,
                    'document_type': document_type,
                    'filename': file_name,
                    'document_date': document_date
                }
                frappe.call({
                    'method': 'mvd.www.emailberatung.new_file_to_beratung',
                    'args': {
                        kwargs
                    }
                });
                upload_files(beratung, key, secret, loop + 1)
            })
        } else {
            upload_files(beratung, key, secret, loop + 1);
        }
    } else {
        var kwargs = {
            'beratung': beratung,
            'raised_by': document.getElementById("email").value
        }
        frappe.call({
            'method': 'mvd.www.emailberatung.send_legacy_mail',
            'args': {
                kwargs
            },
            'async': true,
            'callback': function(res) {
                location.replace('https://www.mieterverband.ch/mv/emailberatung-erfolg');
            }
        });
        
    }
}

function show_mz() {
    localStorage.setItem('mz_anfrage', '1');
    $("#tab_title").text("Mietzinserhöhung");
    $(".mz").css("display", 'inline');
    $("#mz_item").addClass("selected");
    $("#allgmein_item").removeClass("selected");
    
    // remove upload rows
    $(".file-upload-row").each(function(){
        if ($(this).attr('id') != 'default_file_row') {
            $(this).remove();
        }
    });
    
    // clear first upload file
    $("#upload_files_1").val('');
    
    // set first 3 upload rows
    add_new_file_row();
    add_new_file_row();
    $("#upload_files_auswahl_1").val('Mietvertrag');
    $("#upload_files_auswahl_2").val('Mietzinserhöhung');
    $("#upload_files_auswahl_1").attr('readonly', true);
    $("#upload_files_auswahl_2").attr('readonly', true);
    $("label[for='upload_files']").each(function(index,element){
        if (index == 0) {
            $(this).text("1. Mietvertrag");
        } else if (index == 1) {
            $(this).text("2. Mietzinserhöhung");
        } else if (index == 2) {
            $(this).text("Falls vorhanden: weitere Vertragsänderung (Mietzinsherabsetzungen, Mietzinserhöhung, Vergleich, Urteil, Vereinbarung oder einseitige Vertragsänderung)");
        }
    });
    
}

function hide_mz() {
    localStorage.setItem('mz_anfrage', '0');
    $("#datum_mietzinsanzeige").val('');
    $("#tab_title").text("Beratungsanfrage");
    $(".mz").css("display", 'none');
    $("#allgmein_item").addClass("selected");
    $("#mz_item").removeClass("selected");
    
    // remove upload rows
    $(".file-upload-row").each(function(){
        if ($(this).attr('id') != 'default_file_row') {
            $(this).remove();
        }
    });
    
    // clear first upload file
    $("#upload_files_auswahl_1").val('');
    $("#upload_files_auswahl_1").attr('readonly', false);
    $("#upload_files_1").val('');
    $("label[for='upload_files']").each(function(){
        $(this).text("Datei");
    });
    
    $(".awesomplete-delete").each(function(){
        $(this).off('click');
        $(this).empty();
        if (!$(this).prev().prev().prev().attr('readonly')&&$(this).prev().prev().prev().children('input').length < 1) {
            $(this).html('<i class="fa fa-xmark"></i>');
            $(this).click(function(){
                $(this).prev().prev().prev().val('');
            });
        } else if (!$(this).prev().prev().prev().children('input').attr('readonly')&&$(this).prev().prev().prev().children('input').length > 0) {
            $(this).prev().prev().prev().children('input').val('');
        }
    });
}

// AWESOMPLETE
// ----------------------------------------------------------------------------------------------------
function init_awesomplete(input_id) {

    var _ = function (input, o) {
        var me = this;

        // Setup
        this.isOpened = false;

        this.input = $(input);
        this.input.setAttribute("autocomplete", "off");
        this.input.setAttribute("aria-autocomplete", "list");

        o = o || {};

        configure(this, {
            minChars: 0,
            maxItems: 10,
            autoFirst: false,
            data: _.DATA,
            filter: _.FILTER_CONTAINS,
            sort: _.SORT_BYLENGTH,
            item: _.ITEM,
            replace: _.REPLACE
        }, o);

        this.index = -1;

        // Create necessary elements
        this.container = $.create("div", {
            className: "awesomplete",
            around: input
        });

        this.ul = $.create("ul", {
            hidden: "hidden",
            inside: this.container
        });

        this.status = $.create("span", {
            className: "visually-hidden",
            role: "status",
            "aria-live": "assertive",
            "aria-relevant": "additions",
            inside: this.container
        });
        
        this.closing = $.create("span", {
            className: "awesomplete-delete",
            inside: this.container
        });

        // Bind events
        $.bind(this.input, {
            "input": this.evaluate.bind(this),
            "mousedown": this.evaluate.bind(this),
            "focus": this.evaluate.bind(this),
            "blur": this.close.bind(this, { reason: "blur" }),
            "keydown": function(evt) {
                var c = evt.keyCode;

                // If the dropdown `ul` is in view, then act on keydown for the following keys:
                // Enter / Esc / Up / Down
                if(me.opened) {
                    if (c === 13 && me.selected) { // Enter
                        evt.preventDefault();
                        me.select();
                    }
                    else if (c === 27) { // Esc
                        me.close({ reason: "esc" });
                    }
                    else if (c === 38 || c === 40) { // Down/Up arrow
                        evt.preventDefault();
                        me[c === 38? "previous" : "next"]();
                    }
                }
            }
        });

        $.bind(this.input.form, {"submit": this.close.bind(this, { reason: "submit" })});

        $.bind(this.ul, {"mousedown": function(evt) {
            var li = evt.target;

            if (li !== this) {

                while (li && !/li/i.test(li.nodeName)) {
                    li = li.parentNode;
                }

                if (li && evt.button === 0) {  // Only select on left click
                    evt.preventDefault();
                    me.select(li, evt.target);
                }
            }
        }});

        if (this.input.hasAttribute("list")) {
            this.list = "#" + this.input.getAttribute("list");
            this.input.removeAttribute("list");
        }
        else {
            this.list = this.input.getAttribute("data-list") || o.list || [];
        }

        _.all.push(this);
    };
    
    _.prototype = {
        set list(list) {
            if (Array.isArray(list)) {
                this._list = list;
            }
            else if (typeof list === "string" && list.indexOf(",") > -1) {
                    this._list = list.split(/\s*,\s*/);
            }
            else { // Element or CSS selector
                list = $(list);

                if (list && list.children) {
                    var items = [];
                    slice.apply(list.children).forEach(function (el) {
                        if (!el.disabled) {
                            var text = el.textContent.trim();
                            var value = el.value || text;
                            var label = el.label || text;
                            if (value !== "") {
                                items.push({ label: label, value: value });
                            }
                        }
                    });
                    this._list = items;
                }
            }

            if (document.activeElement === this.input) {
                this.evaluate();
            }
        },
        get selected() {
            return this.index > -1;
        },
        get opened() {
            return this.isOpened;
        },
        close: function (o) {
            if (!this.opened) {
                return;
            }

            this.ul.setAttribute("hidden", "");
            this.isOpened = false;
            this.index = -1;

            $.fire(this.input, "awesomplete-close", o || {});
        },
        open: function () {
            this.ul.removeAttribute("hidden");
            this.isOpened = true;

            if (this.autoFirst && this.index === -1) {
                this.goto(0);
            }

            $.fire(this.input, "awesomplete-open");
        },
        next: function () {
            var count = this.ul.children.length;
            this.goto(this.index < count - 1 ? this.index + 1 : (count ? 0 : -1) );
        },
        previous: function () {
            var count = this.ul.children.length;
            var pos = this.index - 1;

            this.goto(this.selected && pos !== -1 ? pos : count - 1);
        },
        // Should not be used, highlights specific item without any checks!
        goto: function (i) {
            var lis = this.ul.children;

            if (this.selected) {
                lis[this.index].setAttribute("aria-selected", "false");
            }

            this.index = i;

            if (i > -1 && lis.length > 0) {
                lis[i].setAttribute("aria-selected", "true");
                this.status.textContent = lis[i].textContent;

                $.fire(this.input, "awesomplete-highlight", {
                    text: this.suggestions[this.index]
                });
            }
        },
        select: function (selected, origin) {
            if (selected) {
                this.index = $.siblingIndex(selected);
            } else {
                selected = this.ul.children[this.index];
            }
            if (selected) {
                var suggestion = this.suggestions[this.index];
                var allowed = $.fire(this.input, "awesomplete-select", {
                    text: suggestion,
                    origin: origin || selected
                });
                if (allowed) {
                    this.replace(suggestion);
                    this.close({ reason: "select" });
                    $.fire(this.input, "awesomplete-selectcomplete", {
                        text: suggestion
                    });
                }
            }
        },
        evaluate: function() {
            var me = this;
            var value = this.input.value;
            if (value.length >= this.minChars && this._list.length > 0) {
                this.index = -1;
                // Populate list with options that match
                this.ul.innerHTML = "";
                this.suggestions = this._list
                    .map(function(item) {
                        return new Suggestion(me.data(item, value));
                    })
                    .filter(function(item) {
                        return me.filter(item, value);
                    })
                    .sort(this.sort)
                    .slice(0, this.maxItems);
                this.suggestions.forEach(function(text) {
                        me.ul.appendChild(me.item(text, value));
                    });
                if (this.ul.children.length === 0) {
                    this.close({ reason: "nomatches" });
                } else {
                    this.open();
                }
            }
            else {
                this.close({ reason: "nomatches" });
            }
        }
    };

    // Static methods/properties
    _.all = [];

    _.FILTER_CONTAINS = function (text, input) {
        return RegExp($.regExpEscape(input.trim()), "i").test(text);
    };

    _.FILTER_STARTSWITH = function (text, input) {
        return RegExp("^" + $.regExpEscape(input.trim()), "i").test(text);
    };

    _.SORT_BYLENGTH = function (a, b) {
        if (a.length !== b.length) {
            return a.length - b.length;
        }
        return a < b? -1 : 1;
    };

    _.ITEM = function (text, input) {
        var html = input.trim() === '' ? text : text.replace(RegExp($.regExpEscape(input.trim()), "gi"), "<mark>$&</mark>");
        return $.create("li", {
            innerHTML: html,
            "aria-selected": "false"
        });
    };

    _.REPLACE = function (text) {
        this.input.value = text.value;
    };

    _.DATA = function (item/*, input*/) { return item; };

    // Private functions
    function Suggestion(data) {
        var o = Array.isArray(data)
          ? { label: data[0], value: data[1] }
          : typeof data === "object" && "label" in data && "value" in data ? data : { label: data, value: data };

        this.label = o.label || o.value;
        this.value = o.value;
    }
    
    Object.defineProperty(Suggestion.prototype = Object.create(String.prototype), "length", {
        get: function() { return this.label.length; }
    });
    
    Suggestion.prototype.toString = Suggestion.prototype.valueOf = function () {
        return "" + this.label;
    };

    function configure(instance, properties, o) {
        for (var i in properties) {
            var initial = properties[i],
                attrValue = instance.input.getAttribute("data-" + i.toLowerCase());
            if (typeof initial === "number") {
                instance[i] = parseInt(attrValue);
            }
            else if (initial === false) { // Boolean options must be false by default anyway
                instance[i] = attrValue !== null;
            }
            else if (initial instanceof Function) {
                instance[i] = null;
            }
            else {
                instance[i] = attrValue;
            }
            if (!instance[i] && instance[i] !== 0) {
                instance[i] = (i in o)? o[i] : initial;
            }
        }
    }

    // Helpers
    var slice = Array.prototype.slice;

    function $(expr, con) {
        return typeof expr === "string"? (con || document).querySelector(expr) : expr || null;
    }

    function $$(expr, con) {
        return slice.call((con || document).querySelectorAll(expr));
    }

    $.create = function(tag, o) {
        var element = document.createElement(tag);
        for (var i in o) {
            var val = o[i];

            if (i === "inside") {
                $(val).appendChild(element);
            }
            else if (i === "around") {
                var ref = $(val);
                ref.parentNode.insertBefore(element, ref);
                element.appendChild(ref);
            }
            else if (i in element) {
                element[i] = val;
            }
            else {
                element.setAttribute(i, val);
            }
        }
        return element;
    };

    $.bind = function(element, o) {
        if (element) {
            for (var event in o) {
                var callback = o[event];
                event.split(/\s+/).forEach(function (event) {
                    element.addEventListener(event, callback);
                });
            }
        }
    };

    $.fire = function(target, type, properties) {
        var evt = document.createEvent("HTMLEvents");
        evt.initEvent(type, true, true );
        for (var j in properties) {
            evt[j] = properties[j];
        }
        return target.dispatchEvent(evt);
    };

    $.regExpEscape = function (s) {
        return s.replace(/[-\\^$*+?.()|[\]{}]/g, "\\$&");
    };

    $.siblingIndex = function (el) {
        /* eslint-disable no-cond-assign */
        for (var i = 0; el = el.previousElementSibling; i++);
        return i;
    };

    // Initialization
    function init() {
        $$("#" + input_id).forEach(function (input) {
            new _(input);
        });
    }

    // Are we in a browser? Check for Document constructor
    if (typeof Document !== "undefined") {
        // DOM already loaded?
        if (document.readyState !== "loading") {
            init();
        }
        else {
            // Wait for it
            document.addEventListener("DOMContentLoaded", init);
        }
    }

    _.$ = $;
    _.$$ = $$;

    // Make sure to export Awesomplete on self when in a browser
    if (typeof self !== "undefined") {
        self.Awesomplete = _;
    }

    // Expose Awesomplete as a CJS module
    if (typeof module === "object" && module.exports) {
        module.exports = _;
    }

    return _;
}

init_awesomplete('upload_files_auswahl_1');
setTimeout(function(){ 
    $(".awesomplete-delete").each(function(){
        $(this).html('<i class="fa fa-xmark"></i>');
        $(this).off('click');
        $(this).click(function(){
            $(this).prev().prev().prev().val('');
        });
    });
}, 1000);
localStorage.setItem('anfage_gesendet', '0');
localStorage.setItem('mz_anfrage', '0');

// AWESOMPLETE END
// ----------------------------------------------------------------------------------------------------
