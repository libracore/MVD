function show_detail_card(mandatsliste) {
    $('.detail').addClass('hidden');
    $('.case-card.active').removeClass('active');
    $(`[data-mandatsliste="${mandatsliste}"]`).addClass('active');
    $(`[data-belongstomandatsliste="${mandatsliste}"]`).removeClass('hidden');
}

function download_zip(mandat) {
    const url =
        "/api/method/mvd.www.va.meine_mandate.download_zip?mandat=" +
        encodeURIComponent(mandat);

    window.open(url, "_blank");
}

function add_fallnummer(mandatsliste) {
    $('main').css('filter', 'blur(5px)');
    frappe.call({
        method: "mvd.www.va.meine_mandate.add_fallnummer",
        args: {
            mandatsliste: mandatsliste,
            fallnummer: $(`#fallnummer-${mandatsliste}`).val()
        },
        freeze: true,
        freeze_message: 'Erfasse Fallnummer...',
        callback: function(r)
        {
            frappe.msgprint(`
                Wir haben die Fallnummer erfasst.<br><br>
                (Diese Meldung schliesst sich in 5s.)`, `Vielen Dank, ${frappe.session.user}!`);
            setTimeout(function(){
                location.reload()
            }, 3000);
        }
    });
}