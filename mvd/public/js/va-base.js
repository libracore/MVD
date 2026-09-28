/*
 * Gemeinsame Basis-Logik für die VA-Extranet-Seiten (mvd/www/va/*).
 * Wird von den Seiten per <script src="/assets/mvd/js/va-base.js"> eingebunden
 * (nach jQuery, vor dem seiteneigenen Script).
 *
 * Aufgabe: Auf schmalen Bildschirmen ist das Layout einspaltig (siehe
 * va-base.css). Dort gibt es keine rechte Spalte, darum wird die
 * Detailansicht direkt unter die angetippte Karte in die Liste geschoben.
 */

/* Breakpoint identisch zu va-base.css, wo .layout einspaltig wird. */
var VA_MOBILE_MQ = window.matchMedia('(max-width: 900px)');

function va_detail_for(mandat) {
    return $('.detail[data-belongstomandat="' + mandat + '"]');
}

/*
 * Detail-Karten je nach Bildschirmbreite einsortieren:
 *   schmal -> direkt hinter die zugehörige Karte in der Liste
 *   breit   -> zurück in die rechte Spalte (direkt in .layout)
 * Die Reihenfolge in .layout entspricht danach wieder der Kartenreihenfolge,
 * also dem serverseitig gerenderten Zustand.
 */
function va_position_details() {
    var mobile = VA_MOBILE_MQ.matches;
    var $layout = $('.layout');

    $('.case-card').each(function() {
        var $card = $(this);
        var $detail = va_detail_for($card.attr('data-mandat'));
        if (!$detail.length) return;

        if (mobile) {
            $detail.addClass('detail-inline');
            $card.after($detail);
        } else {
            $detail.removeClass('detail-inline');
            $layout.append($detail);
        }
    });
}

function show_detail_card(mandat) {
    var $detail = va_detail_for(mandat);

    /* Einspaltig verhält sich die Liste wie ein Akkordeon: nochmaliges
       Antippen der offenen Karte schliesst die Detailansicht wieder. */
    var close_again = VA_MOBILE_MQ.matches && !$detail.hasClass('hidden');

    $('.detail').addClass('hidden');
    $('.case-card.active').removeClass('active');

    if (!close_again) {
        $('[data-mandat="' + mandat + '"]').addClass('active');
        $detail.removeClass('hidden');
    }

    va_position_details();
}

/* Beim Drehen des Geräts / Grössenänderung die Detailansicht mitnehmen. */
if (VA_MOBILE_MQ.addEventListener) {
    VA_MOBILE_MQ.addEventListener('change', va_position_details);
} else if (VA_MOBILE_MQ.addListener) {
    /* Fallback für ältere Safari-/Android-Browser */
    VA_MOBILE_MQ.addListener(va_position_details);
}

$(va_position_details);
