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
