function new_onlineberatung() {
    var kwargs = {
        'mv_mitgliedschaft': document.getElementById("mitgliedschaft_nr").value,
        'mitgliedschafts_typ': document.getElementById("mitgliedschaft_typ").value,
        'anrede': document.getElementById("anrede_0").checked ? 'Frau':'Herr',
        'vorname': document.getElementById("vorname").value,
        'nachname': document.getElementById("nachname").value,
        'telefon': document.getElementById("telefon").value,
        'e_mail': document.getElementById("email").value,
        'strasse': document.getElementById("mo_strasse").value,
        'nummer': document.getElementById("mo_strassen_nr").value,
        'postleitzahl': document.getElementById("mo_plz").value,
        'ort': document.getElementById("mo_ort").value,
        'anderes_mietobjekt': document.getElementById("anderes_mietobjekt").value,
        'frage': document.getElementById("frage").value
    }
    frappe.call({
        method: 'mvd.www.onlineberatung.new_onlineberatung',
        args: {
            kwargs
        }
    });
}

$(':file').on('change',function(){
    var myFile = $(this).val();
    var upld = myFile.split('.').pop();
    if(![".pdf", ".jpg", ".jpeg"].includes(upld)){
        alert("Nur Dateien vom Typ PDF und JPEG/JPG sind erlaubt.");
        $(this).val("");
    }
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

