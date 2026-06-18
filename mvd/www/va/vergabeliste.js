function show_detail_card(mandatsliste) {
    $('.detail').addClass('hidden');
    $('.case-card.active').removeClass('active');
    $(`[data-mandatsliste="${mandatsliste}"]`).addClass('active');
    $(`[data-belongstomandatsliste="${mandatsliste}"]`).removeClass('hidden');
}

function take(mandatsliste, va_in_list) {
    if (va_in_list === 'True') {
        frappe.msgprint(`Du hast dein Interesse für dieses Mandat bereits hinterlegt.`, "Information");
    } else {
        $('main').css('filter', 'blur(5px)');
        frappe.call({
            method: "mvd.www.va.vergabeliste.add_va",
            args: {
                mandatsliste: mandatsliste
            },
            freeze: true,
            freeze_message: 'Erfasse Interesse...',
            callback: function(r)
            {
                frappe.msgprint(`
                    Wir haben dein Interesse registriert.<br><br>
                    Wir melden uns innerhalb der nächsten 48 Stunden bei dir, falls wir dir eines oder mehrere der Mandate übertragen.'<br><br>
                    (Diese Meldung schliesst sich in 5s.)`, `Vielen Dank, ${frappe.session.user}!`);
                setTimeout(function(){
                    location.reload()
                }, 3000);
            }
        });
    }
}