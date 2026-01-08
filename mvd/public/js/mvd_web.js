window.onload = function afterWebPageLoad() { 
    if ((window.location.href.indexOf("/#login") > -1)||(window.location.href.indexOf("/login#login") > -1)) {
        $("#login_email").parent().parent().css("display","none");
        $(".social-logins h6").css("display","none");
        $(".forgot-password-message").css("display","none");
        $(".social-logins").prepend("<h6>Bitte Anmelden mit MV-Login</h6>").css({'padding-top' : '20%'}).addClass("page-card");
        $(".btn-auth0").css({
            'padding' : '0.5rem 1rem',
            'height' : '3em',
            'color' : '#fff',
            'background-color' : '#21539e',
            'border-color': '#21539e'
        }).parent().after("<p>Bei Problemen <a href=\"https://www.mieterverband.ch/kontakt/#11381\">kontaktiert den MVD</a> per E-Mail unter <br> <a href=\"maito:libracore-support@mieterverband.ch\">libracore-support@mieterverband.ch</a></p>");
        $(".fa-key").after("Anmelden mit ");
        
        try {
            // Login Toggler
            locals.login_toggler = 01
            $($(".text-muted.small.col-sm-6.col-12")[0]).on("click", function(){
                login_toggler();
            });
        } catch{}
    }
}

function login_toggler() {
    if (locals.login_toggler == 5) {
        $(".login-content.page-card").css("display", "block");
    } else {
        locals.login_toggler += 1;
    }
}
