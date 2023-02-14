function new_onlineberatung() {
    var kwargs = {
        'mv_mitgliedschaft': document.getElementById("mitgliedschaft_id").value,
        'telefon': document.getElementById("telefon").value,
        'email': document.getElementById("email").value,
        'anderes_mietobjekt': document.getElementById("anderes_mietobjekt").value,
        'frage': document.getElementById("frage").value
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
}

$(':file').on('change',function(){
    var myFile = $(this).val();
    var upld = myFile.split('.').pop();
    if(!["pdf", "jpg", "jpeg", "zip"].includes(upld)){
        alert("Nur Dateien vom Typ PDF und JPEG/JPG sind erlaubt.");
        $(this).val("");
    }
    if(this.files[0].size > 10485760){
       alert("Die Maximale Filegrösse beträgt 10MB.");
       $(this).val("");
    };
})

function add_new_file_row() {
    var new_id = $(':file').length + 1;
    var klon = $("#default_file_row").clone(true);
    klon[0].id = "file_row_" + String(new_id);
    klon[0].children[0].children[0].children[1].id = "upload_files_" + String(new_id);
    klon[0].children[1].children[0].children[1].id = "upload_files_dateupload_files_date_" + String(new_id);
    klon[0].children[2].children[1].id = "upload_files_auswahl_" + String(new_id);
    if ($(':file').length != 1) {
        $("#" + "file_row_" + String($(':file').length)).after(klon);
    } else {
        $("#default_file_row").after(klon);
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
                file_name += $("#upload_files_dateupload_files_date_" + String(loop)).val().replace("-", "_").replace("-", "_") + "_";
            }
            if ($("#upload_files_auswahl_" + String(loop)).val()) {
                file_name += $("#upload_files_auswahl_" + String(loop)).val() + "_";
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
            }).then(upload_files(beratung, key, secret, loop + 1))
        } else {
            upload_files(beratung, key, secret, loop + 1);
        }
    } else {
        location.replace('https://www.mieterverband.ch/mv/emailberatung-erfolg');
    }
}
