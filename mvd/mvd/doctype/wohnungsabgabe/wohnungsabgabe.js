// Copyright (c) 2022, libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on('Wohnungsabgabe', {
    refresh: function(frm) {
        override_default_email_dialog(frm);
    },
    validate: function(frm) {
        totalRechner(frm);
    },
    //total: function(frm) {
    // 		totalRechner(frm);
    //},
    mitgliederdaten_uebernehmen: function(frm) {
    mitgliedschaftsdatenUebernehmen(frm);
    },
    language: function(frm) {
        update_qa_mail_druckvorlage(frm);
    }
});

function override_default_email_dialog(frm) {
    // overwrite E-Mail BTN
    $("[data-label='Email']").parent().off("click");
    $("[data-label='Email']").parent().click(function(){frappe.mvd.new_mail(cur_frm);});
    $("[data-label='E-Mail']").parent().off("click");
    $("[data-label='E-Mail']").parent().click(function(){frappe.mvd.new_mail(cur_frm);});
    $(".btn.btn-default.btn-new-email.btn-xs").off("click");
    $(".btn.btn-default.btn-new-email.btn-xs").click(function(){frappe.mvd.new_mail(cur_frm);});
    $("[data-communication-type='Communication']").off("click");
    $(".reply-link").off("click");
    $(".reply-link").click(function(e){prepare_mvd_mail_composer(e);}); 
    $(".reply-link-all").click(function(e){prepare_mvd_mail_composer(e);});
    frappe.ui.keys.off('ctrl+e', cur_frm.page);
}

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


function prepare_mvd_mail_composer(e, forward=false) {
    var last_email = null;
    var default_sender = frappe.boot.default_beratungs_sender || '';

    const $target = $(e.currentTarget);
    const name = $target.data().name ? $target.data().name:e.currentTarget.closest(".timeline-item").getAttribute("data-name");
    
    // find the email to reply to
    cur_frm.timeline.get_communications().forEach(function(c) {
        if(c.name == name) {
            last_email = c;
            return false;
        }
    });
    if (last_email.sender.includes(".mieterverband.ch")){
        last_email.sender = cur_frm.doc.e_mail_1 || '';
    }
    
    const opts = {
        doc: cur_frm.doc,
        txt: "",
        title: forward ? __('Forward'):__('Reply'),
        frm: cur_frm,
        sender: default_sender,
        last_email,
        is_a_reply: true,
        subject: forward ? __("Fw: {0}", [last_email.subject]):''
    };

    if ($target.is('.reply-link-all')) {
        if (last_email) {
            opts.cc = last_email.cc;
            opts.bcc = last_email.bcc;
        }
    }

    // make the composer
    new frappe.mvd.MailComposer(opts);
}

function update_qa_mail_druckvorlage(frm) {
    if (cur_frm.doc.language === 'de') {
        frm.set_value('qa_mail_druckvorlage', 'Wohnungsabgabe-MVBE');
    } else if (cur_frm.doc.language === 'fr') {
        frm.set_value('qa_mail_druckvorlage', 'Wohnungsabgabe, FR-MVBE');
    } else {
        frm.set_value('qa_mail_druckvorlage', null);
    }
}