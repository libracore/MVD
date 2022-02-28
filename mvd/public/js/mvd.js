// Copyright (c) 2021-2022, libracore AG and contributors
// For license information, please see license.txt

// add links to MVD wiki
frappe.provide('frappe.help.help_links');
frappe.call({
    method: 'mvd.mvd.doctype.mv_help_links.mv_help_links.get_help_links',
    callback: function(r) {
        if(r.message) {
            var links = r.message;
            for (var i = 0; i < links.length; i++) {
                frappe.help.help_links['List/' + links[i].doctype_link] = [
                    { label: links[i].label, url: links[i].url },
                ];
                frappe.help.help_links['Form/' + links[i].doctype_link] = [
                    { label: links[i].label, url: links[i].url },
                ];
                frappe.help.help_links['Tree/' + links[i].doctype_link] = [
                    { label: links[i].label, url: links[i].url },
                ];
            }
        } 
    }
});

// Redirect to VBZ after login, reset user default and set navbar color to red if test
$(document).ready(function() {
    // reset user company default
    frappe.defaults.set_user_default_local("Company", '');
    
    // mark navbar in specific colour
    setTimeout(function(){
        var navbars = document.getElementsByClassName("navbar");
        if (navbars.length > 0) {
            if ((window.location.hostname.includes("test-libracore")) || (window.location.hostname.includes("localhost")) || (window.location.hostname.includes("192.168.0.18"))) {
                navbars[0].style.backgroundColor = "#B0473A";
            }
        }
    }, 2000);
    
    if(frappe._cur_route==""||frappe._cur_route=="#") {
        window.location.href = "#vbz";
        
        // zwangs reload für den Moment ausgesetzt
        //~ frappe.dom.freeze('Lade Verarbeitungszentrale...');
        //~ setTimeout(function(){
            //~ frappe.dom.freeze('Lade Verarbeitungszentrale...');
            //~ location.reload();
        //~ }, 100);
    }
    
    
});

// Redirect to VBZ after click on Navbar Desk Shortcut
$(document).on('click','#navbar-breadcrumbs a, a.navbar-home',function(event){
    var navURL = event.currentTarget.href;

    if(navURL.endsWith("#")) {
        event.currentTarget.href = '#vbz';
        
        // zwangs reload für den Moment ausgesetzt
        //~ frappe.dom.freeze('Lade Verarbeitungszentrale...');
        //~ setTimeout(function(){
            //~ frappe.dom.freeze('Lade Verarbeitungszentrale...');
            //~ location.reload();
        //~ }, 100);
    }
});
