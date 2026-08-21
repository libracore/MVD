$(document).on('click', '.kostengutsprache-cell', function() {
    const rsvmitglied = $(this).data('rsvmitglied');
    kostengutsprache_click(rsvmitglied);
});

$(document).on('click', '.abgelehnt-cell', function() {
    const rsvmitglied = $(this).data('rsvmitglied');
    abgelehnt_click(rsvmitglied);
});

$(document).on('click', '.fallnummer-cell', function() {
    const rsvmitglied = $(this).data('rsvmitglied');
    const rsvmandat = $(this).data('rsvmandat');
    fallnummer_speichern(rsvmitglied, rsvmandat);
});


function kostengutsprache_click(rsvmitglied) {
    frappe.call({
        method: "mvd.www.va.coop_mandate.erteile_kostenfreigabe",
        args: {
            rsvmitglied: rsvmitglied
        },
        freeze: true,
        freeze_message: 'Erteile Kostenfreigabe...',
        callback: function(r)
        {
            location.reload();
        }
    });
}

function abgelehnt_click(rsvmitglied) {
    frappe.call({
        method: "mvd.www.va.coop_mandate.ablehnung",
        args: {
            rsvmitglied: rsvmitglied
        },
        freeze: true,
        freeze_message: 'Erteile Ablehnung...',
        callback: function(r)
        {
            location.reload();
        }
    });
}

function fallnummer_speichern(rsvmitglied, rsvmandat) {
    if (rsvmitglied) {
        $('#fallnummer-dialog')
        .data('rsvmitglied', rsvmitglied)
        .modal('show');
    }
    if (rsvmandat) {
        $('#fallnummer-dialog')
        .data('rsvmandat', rsvmandat)
        .modal('show');
    }
}
$('#fallnummer-speichern').on('click', function() {
    const rsvmitglied = $('#fallnummer-dialog').data('rsvmitglied');
    const rsvmandat = $('#fallnummer-dialog').data('rsvmandat');
    const fallnummer = $('#fallnummer').val().trim();

    if (!fallnummer ) {
        frappe.msgprint('Bitte erfassen sie die Fallnummer');
        return;
    }
    let _args = {}
    if (rsvmitglied) {
        _args = {
            rsvmitglied: rsvmitglied,
            fallnummer: fallnummer
        }
    } else if (rsvmandat) {
        _args = {
            rsvmandat: rsvmandat,
            fallnummer: fallnummer
        }
    }

    $('#fallnummer-dialog').modal('hide');
    $('main').css('filter', 'blur(5px)');
    frappe.call({
        method: "mvd.www.va.coop_mandate.add_fallnummer",
        args: _args,
        freeze: true,
        freeze_message: 'Erfasse Fallnummer...',
        callback: function(r)
        {
            location.reload();
        }
    });
});