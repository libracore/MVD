function show_detail_card(mandat) {
    $('.detail').addClass('hidden');
    $('.case-card.active').removeClass('active');
    $(`[data-mandat="${mandat}"]`).addClass('active');
    $(`[data-belongstomandat="${mandat}"]`).removeClass('hidden');
}

function download_zip(mandat) {
    _download_zip(mandat);
}
function _download_zip(mandat) {
    const url =
        "/api/method/mvd.www.va.meine_mandate.download_zip?mandat=" +
        encodeURIComponent(mandat);

    window.open(url, "_blank");
}

function close_rsvmitglied(rsv_mitglied) {
    $('main').css('filter', 'blur(5px)');
    frappe.call({
        method: "mvd.www.va.meine_mandate.close_rsvmitglied",
        args: {
            rsv_mitglied: rsv_mitglied
        },
        freeze: true,
        freeze_message: 'Schliesse RSV-Mitglied...',
        callback: function(r)
        {
            frappe.msgprint(`
                Wir haben das RSV-Mitglied geschlossen.<br><br>
                (Diese Meldung schliesst sich in 5s.)`, `Vielen Dank, ${frappe.session.user}!`);
            setTimeout(function(){
                location.reload()
            }, 3000);
        }
    });
}

$('#mandate-filter').on('change', function() {
    const value = $(this).val();

    if (value === 'open') {
        $('[data-closestatus="1"]').hide();
        $('[data-closestatus="0"]').show();
    } else if (value === 'closed') {
        $('[data-closestatus="0"]').hide();
        $('[data-closestatus="1"]').show();
    } else {
        $('[data-closestatus]').show();
    }
});

function close_rsvmandat(rsv_mandat) {
    // Felder zurücksetzen
    $('#verfahrensinstanz').val('');
    $('#feedback').val('');
    $('#abschluss-datei').val('');
    $('#feedback-required').hide();
    $('#feedback-hinweis').hide();

    $('#fragen-dialog')
        .data('rsv-mandat', rsv_mandat)
        .modal('show');
}


$('#verfahrensinstanz').on('change', function() {
    const verfahrensinstanz = parseInt($(this).val());

    if (verfahrensinstanz > 1) {
        $('#feedback-required').show();
        $('#feedback-hinweis').show();
        $('#feedback').attr('required', true);
    } else {
        $('#feedback-required').hide();
        $('#feedback-hinweis').hide();
        $('#feedback').removeAttr('required');
    }
});


$('#fragen-speichern').on('click', function() {
    const rsv_mandat = $('#fragen-dialog').data('rsv-mandat');
    const verfahrensinstanz = $('#verfahrensinstanz').val();
    const feedback = $('#feedback').val().trim();
    const file_input = $('#abschluss-datei')[0];
    const file = file_input.files.length > 0
        ? file_input.files[0]
        : null;

    if (!verfahrensinstanz) {
        frappe.msgprint('Bitte eine Verfahrensinstanz auswählen.');
        return;
    }

    if (parseInt(verfahrensinstanz) > 1 && !feedback) {
        frappe.msgprint('Bitte ein Feedback eingeben.');
        $('#feedback').focus();
        return;
    }

    $('#fragen-dialog').modal('hide');

    if (file) {
        upload_file(
            file,
            rsv_mandat,
            verfahrensinstanz,
            feedback
        );
    } else {
        finish_rsvmandat(
            rsv_mandat,
            verfahrensinstanz,
            feedback
        );
    }
});


function upload_file(file, rsv_mandat, verfahrensinstanz, feedback) {
    const form_data = new FormData();
    form_data.append('file', file);
    form_data.append('doctype', 'RSVMandat');
    form_data.append('docname', rsv_mandat);
    form_data.append('is_private', 1);

    $.ajax({
        url: '/api/method/upload_file',
        type: 'POST',
        data: form_data,
        processData: false,
        contentType: false,

        beforeSend: function(xhr) {
            xhr.setRequestHeader(
                'X-Frappe-CSRF-Token',
                frappe.csrf_token
            );
        },

        success: function(r) {
            finish_rsvmandat(
                rsv_mandat,
                verfahrensinstanz,
                feedback
            );
        },

        error: function(xhr, status, error) {
            frappe.msgprint(
                'Die Datei konnte nicht hochgeladen werden.<br><br>' +
                'Fehler: ' + error
            );
        }
    });
}


function finish_rsvmandat(rsv_mandat, verfahrensinstanz, feedback) {
    frappe.call({
        method: "mvd.www.va.meine_mandate.close_rsvmandat",
        args: {
            rsv_mandat: rsv_mandat,
            verfahrensinstanz: verfahrensinstanz,
            feedback: feedback
        },
        freeze: true,
        freeze_message: 'Schliesse RSV-Mandat...',
        callback: function(r) {
            frappe.msgprint(`
                Wir haben das RSV-Mandat geschlossen.<br><br>
                (Diese Meldung schliesst sich in 5s.)
            `, `Vielen Dank, ${frappe.session.user}!`);
            setTimeout(function() {
                location.reload();
            }, 3000);
        }
    });
}