/*global jQuery */
/*jslint white: true, browser: true, onevar: true, undef: true, nomen: true, eqeqeq: true, bitwise: true, regexp: true, newcap: true, strict: true */
/**
 * jQuery plugin for posting form including file inputs.
 * 
 * Copyright (c) 2010 Ewen Elder
 *
 * Licensed under the MIT and GPL licenses:
 * http://www.opensource.org/licenses/mit-license.php
 * http://www.gnu.org/licenses/gpl.html
 *
 * @author: Ewen Elder <glomainn at yahoo dot co dot uk> <ewen at jainaewen dot com>
 * @version: 1.0.1 (2010-07-22)
**/

'use strict';
(function ($) {
    $.fn.iframePostForm = function (options) {
        var contents, elements, element, iframe;
        
        elements = $(this);
        options = $.extend({}, $.fn.iframePostForm.defaults, options);
        
        // Add the iframe.
        if (!$('#' + options.iframeID).length) {
            $('body').append('<iframe name="' + options.iframeID + '" id="' + options.iframeID + '" style="display:none"></iframe>');
        }

        return elements.each(function () {
            element = $(this);
            // Target the iframe.
            element.attr('target', options.iframeID);
            // Submit listener.
            element.submit(function() {
                options.post.apply(this);
                iframe = $('#' + options.iframeID);
                iframe.one('load', function() {
                    options.complete.apply(this, [$("#" + this.id).contents().text()]);
                    setTimeout(function() {
                        $("#" + this.id).contents().text('');
                    }, 1);
                });
            });
        });
    };
    
    $.fn.iframePostForm.defaults = {
        iframeID : 'iframe-post-form',       // IFrame ID.
        post : function () {},               // Form onsubmit.
        complete : function (response) {}    // After everything is completed.
    };
})(jQuery);

/**
 * End Jquery Plugin.
 * Begin RedHen LGPL.
 */

function got_results(response) { //Once the server has responded
        response = $.parseJSON(response);
        if(response[0] == "InputError") {
            alert("Invalid Input.")
            return
        }
        var results_bar = Array(); //List the spectra in the results bar
        var spectra = Array(); //Hold data
        var colors = ['red', 'blue', 'green', 'orange', 'purple'];
        $.each(response, function(i, spectrum) {
            results_bar.push('<div style="color:'+colors[i]+'">'+spectrum[1]+'</div>');
            spectra.push(new Spectrum(spectrum[1], spectrum[3], colors[i]));
        });
        $('#results').html(results_bar.join(' '));
        var selected = 0;
        var vertical_divs = Array(); //Prepare the lines on the screen
        $.each(spectra, function(i, spectrum) { //For each spectrum to be graphed
            for(var x=0; x<$('#graph').width(); x++) { //For each point in the spectrum
                var y = Math.floor(spectrum.data[x]); if(x>0) var oldy = Math.floor(spectrum.data[x-1]); else var oldy = y; //get the y data
                if(y>oldy) vertical_divs.push('<div class="graph-line" style="background-color:'+spectrum.color+'; left:'+x+'px; height:'+(y-oldy)+'px; bottom:'+oldy+'px;"></div>'); //Make an upward rectangle
                else if(y<oldy) vertical_divs.push('<div class="graph-line" style="background-color:'+spectrum.color+'; left:'+x+'px; height:'+(oldy-y)+'px; bottom:'+y+'px;"></div>'); //or make a downward rectangle
                else vertical_divs.push('<div class="graph-line" style="background-color:'+spectrum.color+'; left:'+x+'px; height:1px; bottom:'+y+'px;"></div>'); //or make a horizontal rectangle
            }}); //Done processing spectra
        vertical_divs.push('<div id="floatybar" class="graph-floatybar">0,0</div>'); //Make floating sign
        vertical_divs.push('<div id="tracepoint" class="graph-trace"></div>'); //Make trace point
        $('#graph').html(vertical_divs.join('')); //Put it all in the graph
        $('#graph').mousemove( function(e) { //Add functions to the graph
            document.body.style.cursor="crosshair";
            var x = Math.floor(e.pageX - $('#graph').position().left);
            $('#floatybar').css('left', x);
            $('#floatybar').css('bottom', spectra[selected].data[x]);
            $('#floatybar').html(x+', '+spectra[selected].data[x]);
            $('#floatybar').show();
            $('#tracepoint').css('left', x-2);
            $('#tracepoint').css('bottom', spectra[selected].data[x]-2);
            $('#tracepoint').show();
        });
        $('#graph').click( function(e) {
            var x = Math.floor(e.pageX - $('#graph').position().left);
            var y = 300+$('#graph').position().top-e.pageY;
            for(var i in spectra) if(Math.abs(spectra[i].data[x]-y)<15) { selected=i; break; }
        });
        $('#graph').mouseout( function(e) {
            $('#floatybar').hide();
            $('#tracepoint').hide();
            document.body.style.cursor="default";
        });
};

function unload(file) {
    $('#checkbox_'+file).hide();
    var action = function(response) { alert('Deleted '+file+' from server.'); };
    $.ajax({ url: '/api', success: action });
}

function add_to_list(s) {
    if( !s ) return;
    var id = String(s).replace('.','_');
    $('#loaded_list').html('<div id="checkbox_'+id+'"><input type="checkbox" checked="yes" onclick="unload(\''+id+'\');" />'+s+'</div>');
    $('#loaded_list').show();
}
 
function combobox_clicked(text) {
    $('#combobox_text').val(text);
    $('#combobox_dropdown').hide();
    $('#combobox_text').focus();
}

$('#browse_button').click(function() {
    var selected = $('#browse_options option:selected').val();
    $('#browse_dialog').show();
    $('#combobox_text').focus();
});

function Spectrum(name, data, color) //Spectrum class
{
    this.name = name; this.data = data; this.color = color;
}

$('#compare_button').click(function() {
    var selected = $('#compare_options option:selected').val();
    $('#loaded_list').hide();
    $('body').css('padding', '0px');
    $('#results').html('Getting results...');
    $('#graph').show();
    $('#results').show();
    $("#upload_form").submit()
});

$('#browse_options').change(function() {
    //Make file upload frame go away when not selected
    var selected = $('#browse_options option:selected').val();
    if(selected=='my computer') $('#file').show(); else $('#file').hide();
});

$('#done_button').click(function() {
    $('#browse_dialog').hide();
    add_to_list($('#combobox_text').val());
    $('#combobox_text').val('');
    $('#combobox_dropdown').hide();
    $('#combobox_dropdown').html('');
});

$('#combobox_text').keyup(function(key) {
    var unicode = key.keyCode ? key.keyCode : key.charCode;
    if(unicode==13) $('#done_button').click();
    if($('#combobox_text').val().length<4) return;
    $('#combobox_dropdown').load( '/api', $('#combobox_text').val() )
    $('#combobox_dropdown').show();
});

$('#file').change(function() {
    if(this.value) {
        $('#file').unbind('mouseout')
        $('#file').unbind('change')
        add_to_list(this.value.match('[^\\\\]+$'));
    }
});

$(document).ready(function() {
    session_id = Math.floor(Math.random()*1e12)+(new Date()).getTime(); //Unique ID so the server can distinguish clients
    $('#upload_form').iframePostForm({
        complete: got_results
    });
});
