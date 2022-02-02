// Copyright (c) 2021-2022, libracore AG and contributors
// For license information, please see license.txt

// add links to senstech wiki
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

setTimeout(function(){$('.nav.navbar-nav.navbar-right').prepend('<li class="dropdown dropdown-mobile"><a class"dropdown-toggle" href="#vbz"><span id="ts_indicator" class=""><i class="fa fa-inbox"></i></span></a></li>');}, 1000);

$(document).ready(function() {
    // Redirect to VBZ after login
    if(frappe._cur_route==""||frappe._cur_route=="#") {
        window.location.href = "#vbz";
    }
});

$(document).on('click','#navbar-breadcrumbs a, a.navbar-home',function(event){
    var navURL = event.currentTarget.href;

    if(navURL.endsWith("#")) {
        event.currentTarget.href = '#vbz';
    }
});
