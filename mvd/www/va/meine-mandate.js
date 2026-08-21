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

function close_rsvmandat(rsv_mandat) {
    $('#fragen-dialog')
        .data('rsv-mandat', rsv_mandat)
        .modal('show');
}
$('#fragen-speichern').on('click', function() {
    const rsv_mandat = $('#fragen-dialog').data('rsv-mandat');
    const frage_1 = $('#frage-1').val().trim();
    const frage_2 = $('#frage-2').val().trim();
    const frage_3 = $('#frage-3').val().trim();

    if (!frage_1 || !frage_2 || !frage_3) {
        frappe.msgprint('Bitte alle drei Fragen beantworten.');
        return;
    }

    console.log(frage_1);
    console.log(frage_2);
    console.log(frage_3);

    $('#fragen-dialog').modal('hide');
    $('main').css('filter', 'blur(5px)');
    frappe.call({
        method: "mvd.www.va.meine_mandate.close_rsvmandat",
        args: {
            rsv_mandat: rsv_mandat
        },
        freeze: true,
        freeze_message: 'Schliesse RSV-Mandat...',
        callback: function(r)
        {
            frappe.msgprint(`
                Wir haben das RSV-Mandat geschlossen.<br><br>
                (Diese Meldung schliesst sich in 5s.)`, `Vielen Dank, ${frappe.session.user}!`);
            setTimeout(function(){
                location.reload()
            }, 3000);
        }
    });
});

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