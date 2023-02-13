function new_onlineberatung() {
    var kwargs = {
        'mv_mitgliedschaft': document.getElementById("mitgliedschaft_id").value,
        'telefon': document.getElementById("telefon").value,
        'email': document.getElementById("email").value,
        'anderes_mietobjekt': document.getElementById("anderes_mietobjekt").value,
        'frage': document.getElementById("frage").value
    }
    frappe.call({
        method: 'mvd.www.emailberatung.new_beratung',
        args: {
            kwargs
        }
    });
}

$(':file').on('change',function(){
    var myFile = $(this).val();
    var upld = myFile.split('.').pop();
    console.log(upld)
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

