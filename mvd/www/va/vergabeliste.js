function show_detail_card(mandat) {
    $('.detail').addClass('hidden');
    $('.case-card.active').removeClass('active');
    $(`[data-mandat="${mandat}"]`).addClass('active');
    $(`[data-belongstomandat="${mandat}"]`).removeClass('hidden');
}

function take(mandat, va_in_list) {
    if (va_in_list === 'True') {
        $('main').css('filter', 'blur(5px)');
        frappe.call({
            method: "mvd.www.va.vergabeliste.remove_va",
            args: {
                mandat: mandat
            },
            freeze: true,
            freeze_message: 'Entferne Interesse...',
            callback: function(r)
            {
                frappe.msgprint(`
                    Wir haben dein Interesse entfernt.<br><br>
                    (Diese Meldung schliesst sich in 5s.)`, `Vielen Dank, ${frappe.session.user}!`);
                setTimeout(function(){
                    location.reload()
                }, 3000);
            }
        });
    } else {
        $('main').css('filter', 'blur(5px)');
        frappe.call({
            method: "mvd.www.va.vergabeliste.add_va",
            args: {
                mandat: mandat,
                bemerkung: $(`#message-${mandat}`).val()
            },
            freeze: true,
            freeze_message: 'Erfasse Interesse...',
            callback: function(r)
            {
                frappe.msgprint(`
                    Wir haben dein Interesse registriert.<br><br>
                    Wir melden uns bei dir, falls wir dir eines oder mehrere der Mandate übertragen.<br><br>
                    (Diese Meldung schliesst sich in 5s.)`, `Vielen Dank, ${frappe.session.user}!`);
                setTimeout(function(){
                    location.reload()
                }, 3000);
            }
        });
    }
}