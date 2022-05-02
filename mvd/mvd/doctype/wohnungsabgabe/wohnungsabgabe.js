// Copyright (c) 2022, libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on('Wohnungsabgabe', {
         refresh: function(frm) {
         	  	//frm.add_custom_button(__("Mitgliedschaftsdaten übernehmen"),  function() {
         			//mitgliedschaftsdatenUebernehmen(frm);
              //  		});
         },
	 validate: function(frm) {
	 		totalRechner(frm);
	},
	//total: function(frm) {
	// 		totalRechner(frm);
	//},
  mitgliederdaten_uebernehmen: function(frm) {
    mitgliedschaftsdatenUebernehmen(frm);
  }

});

function mitgliedschaftsdatenUebernehmen(frm) {
    frappe.call({
        'method': "frappe.client.get",
        'args': {
            'doctype': "Mitgliedschaft",
            'name': cur_frm.doc.mv_mitgliedschaft
        },
        'callback': function(response) {
            var mitgliedschaft = response.message;
            cur_frm.set_value("mitglied_nr", mitgliedschaft.mitglied_nr);
            cur_frm.set_value("language", mitgliedschaft.language);
            cur_frm.set_value("adressblock", mitgliedschaft.adressblock);
            cur_frm.set_value("briefanrede", mitgliedschaft.briefanrede);
            cur_frm.set_value("firma", mitgliedschaft.firma);
            cur_frm.set_value("anrede_c", mitgliedschaft.anrede_c);
            cur_frm.set_value("nachname_1", mitgliedschaft.nachname_1);
            cur_frm.set_value("vorname_1", mitgliedschaft.vorname_1);
            cur_frm.set_value("tel_p_1", mitgliedschaft.tel_p_1);
            cur_frm.set_value("tel_m_1", mitgliedschaft.tel_m_1);
            cur_frm.set_value("e_mail_1", mitgliedschaft.e_mail_1);
            if ( mitgliedschaft.abweichende_objektadresse ) {
              var strasse_nummer_zusatz = mitgliedschaft.objekt_strasse+" "+mitgliedschaft.objekt_hausnummer+" "+mitgliedschaft.objekt_nummer_zu;
              cur_frm.set_value("plz", mitgliedschaft.objekt_plz);
              cur_frm.set_value("ort", mitgliedschaft.objekt_ort);
            } else {
              var strasse_nummer_zusatz = mitgliedschaft.strasse+" "+mitgliedschaft.nummer+" "+mitgliedschaft.nummer_zu;
              cur_frm.set_value("plz", mitgliedschaft.plz);
              cur_frm.set_value("ort", mitgliedschaft.ort);
            }
            cur_frm.set_value("strasse_nummer_zusatz", strasse_nummer_zusatz);
            if (mitgliedschaft.abweichende_rechnungsadresse ) {
              cur_frm.set_value("rechnungsadresse", mitgliedschaft.rg_adressblock);
            }
	    // hier die nächste Zeile…
        }
    });
}

function totalRechner(frm) {
  var tarif_01 = parseFloat(cur_frm.doc.tarif_01);
  console.log('tarif_01 '+tarif_01);
  var tarif_02 = parseFloat(cur_frm.doc.tarif_02);
  var tarif_03 = parseFloat(cur_frm.doc.tarif_03);
  var tarif_04 = parseFloat(cur_frm.doc.tarif_04);
  var tarif_05 = parseFloat(cur_frm.doc.tarif_05);
  var tarif_06 = parseFloat(cur_frm.doc.tarif_06);
  var tarif_07 = parseFloat(cur_frm.doc.tarif_07);
  var weg_01 = parseFloat(cur_frm.doc.weg_01);
  var weg_02 = parseFloat(cur_frm.doc.weg_02);
  var weg_03 = parseFloat(cur_frm.doc.weg_03);
  var weg_04 = parseFloat(cur_frm.doc.weg_04);
  var nichtmitgliederzuschlag = parseFloat(cur_frm.doc.nichtmitgliederzuschlag);
	var total = tarif_01 + tarif_02 + tarif_03 + tarif_04 + tarif_05 + tarif_06 + tarif_07 + weg_01 + weg_02 + weg_03 + weg_04 + nichtmitgliederzuschlag;
  //console.log('menno: '+tarif_01 + tarif_02 + tarif_03 + tarif_04 + tarif_05 + tarif_06 + tarif_07 + weg_01 + weg_02 + weg_03 + weg_04 + nichtmitgliederzuschlag);

  console.log(total);
  total = parseFloat(total).toFixed(2);
  cur_frm.set_value("total", total);
};
