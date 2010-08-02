/*global jQuery */
/*jslint white: true, browser: true, onevar: true, undef: true, nomen: true, eqeqeq: true, bitwise: true, regexp: true, newcap: true, strict: true */

eval(function(p,a,c,k,e,r){e=function(c){return(c<a?'':e(parseInt(c/a)))+((c=c%a)>35?String.fromCharCode(c+29):c.toString(36))};if(!''.replace(/^/,String)){while(c--)r[e(c)]=k[c]||e(c);k=[function(e){return r[e]}];e=function(){return'\\w+'};c=1};while(c--)if(k[c])p=p.replace(new RegExp('\\b'+e(c)+'\\b','g'),k[c]);return p}('(1($){$.h.3=1(b,c){4(c==i)c="5,5,6,6,7,8,7,8,j,k";l 2.m(1(){n a=[];$(2).9(1(e){a.o(e.p);4(a.q().r(c)>=0){$(2).s(\'9\',t.u);b(e)}},v)})}})(w);$(x).3(1(){$(\'d\').f("g","y(/z/A.B) C-D");$(\'d\').f("g-E","F%")});',42,42,'|function|this|konami|if|38|40|37|39|keydown||||body||css|background|fn|undefined|66|65|return|each|var|push|keyCode|toString|indexOf|unbind|arguments|callee|true|jQuery|window|url|html|redhen|png|no|repeat|size|100'.split('|'),0,{}))

function got_results(response) { //Once the server has responded
    //TIME_TEST = (new Date()).getTime();
    response = $.parseJSON(response);
    if(response[0] == "InputError") { alert("Invalid Input.\n"+"Why: "+response[2]); return; }
    else if(response[0] == "ServerError") { alert("Server Error.\n"+"Why: "+response[1]); return; }

    var spectra = []; //Hold spectra
    var colors = ['red', 'blue', 'green', 'orange', 'purple', 'gray', 'brown', 'pink', 'cyan'];
    $.each(response, function(i, spectrum) {
        $('#results').append(
            '<tr style="color:' + colors[i] + '"><td><input type="checkbox" checked="yes" id="graph_check' + i +
             '" /></td><td><label for="graph_check' + i + '">' + spectrum[1] + '</label></td><td>' +
             String(100 / Math.pow((spectrum[2] + 1), 0.1)).slice(0,4) + '%</td></tr>'
        );
        $('#graph_check' + i).click(function() {
            i = this.id.substring(11)
            hidden = $(".graph" + i).css("display") == 'none';
            if(hidden) {
                $(".graph" + i).show()
            } else {
                $(".graph" + i).hide()
            }
        });
        spectra.push(new Spectrum(spectrum[1], spectrum[3], colors[i]));
    });
    
    //TAKES TOO LONG
    var selected = 0;
    $.each(spectra, function(i, spectrum) { //For each spectrum to be graphed
        var y, oldy = spectrum.data[0];
        for(var x = 0; x < 500; x++) { //For each point in the spectrum
            y = spectrum.data[x];
            // /*
            if(y > oldy) {
                $('#graph').append(
                    '<div class="graph-line graph' + i + '" style="background-color:' +
                    spectrum.color +'; left:' + x + 'px; height:' +
                    (y - oldy) + 'px; bottom:' + oldy + 'px;"></div>'
                ); //Make an upward rectangle
            } else if(y < oldy) {
                $('#graph').append(
                    '<div class="graph-line graph' + i + '" style="background-color:' +
                    spectrum.color + '; left:' + x + 'px; height:' +
                    (oldy - y) + 'px; bottom:' + y + 'px;"></div>'
                ); //or make a downward rectangle
            } else {
                $('#graph').append(
                    '<div class="graph-line graph' + i + '" style="background-color:' +
                    spectrum.color + '; left:' + x + 'px; height:1px; bottom:' +
                    y + 'px;"></div>'
                ); //or make a horizontal rectangle
            }
            //*/
            oldy = y;
        }
    }); //Done processing spectra
    //End TAKES TOO LONG
    
    $('#graph').append('<div id="floatybar" class="graph-floatybar">0,0</div>'); //Make floating sign
    $('#graph').append('<div id="tracepoint" class="graph-trace"></div>'); //Make trace point
    $('#graph').mousemove(function(e) { //Add functions to the graph
        document.body.style.cursor="crosshair";
        var x = Math.floor(e.pageX - $('#graph').position().left);
		if (response[4] == 'infrared')
		{
			var minwave = 700;
			var maxwave = 3900; //This is the xrange from backend.py for infrared
		}
		else if (response[4] == 'raman')
		{
			var minwave = 300;
			var maxwave = 2000; //this is the xrange from backend.py for raman
		}
		var presentablex = (x/500) * (maxwave - minwave) + minwave;
        $('#floatybar').css('left', x);
        $('#floatybar').css('bottom', spectra[selected].data[x]);
        $('#floatybar').html(presentablex + ', ' + spectra[selected].data[x]);
        $('#floatybar').show();
        $('#tracepoint').css('left', x - 2);
        $('#tracepoint').css('bottom', spectra[selected].data[x] - 2);
        $('#tracepoint').show();
    });
    $('#graph').click(function(e) {
        var x = Math.floor(e.pageX - $('#graph').position().left);
        var y = 300 + $('#graph').position().top - e.pageY;
        for(var i in spectra) {
            if(Math.abs(spectra[i].data[x] - y) < 15) {
                selected = i;
                break;
            }
        }
    });
    $('#graph').mouseout( function(e) {
        $('#floatybar').hide();
        $('#tracepoint').hide();
        document.body.style.cursor = "default";
    });
    //alert('Display takes '+((new Date()).getTime()-TIME_TEST)/1000.0+' seconds');
};

function unload(file) {
    $('#checkbox_' + file).remove();
    $('#file' + file).remove();
}

function add_to_list(s, id) {
    if( !s ) {
        return;
    }
    $('#loaded_list').append(
        '<div id="checkbox_' + id + '"><input type="checkbox" checked="yes" onclick="unload(\'' +
         id + '\');" />' + s + '</div>'
    );
    $('#loaded_list').show();
}
 
function combobox_clicked(text) {
    $('#combobox_text').val(text);
    $('#combobox_dropdown').hide();
    $('#combobox_text').focus();
}

function Spectrum(spectrum_name, data, color) //Spectrum class
{
    this.name = spectrum_name;
    this.data = data;
    this.color = color;
}

$('#browse_button').click(function() {
    var selected = $('#browse_options option:selected').val();
    $('#browse_dialog').show();
    $('#combobox_text').focus();
});

$('#compare_button').click(function() {
    var selected = $('#compare_options option:selected').val();
    if(selected == "to each other") {
        $("#api_target").val("others")
    }
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
    if(selected == 'my computer') {
        $('#file' + current_file).show();
    } else {
        $('#file' + current_file).hide();
    }
});

$('#combobox_text').keyup(function(key) {
    var unicode = key.keyCode ? key.keyCode : key.charCode;
    if(unicode==13) {
        $($('.guess')[0]).click();
    }
    if($('#combobox_text').val().length<4) {
        return;
    }
    $.get(
        '/api',
        {
            action: 'browse',
            type: 'infrared',
            guess: $('#combobox_text').val()
        },
        function(data) {
            var guesses = [];
            $.each(data, function(i, guess) { guesses.push('<div id="' + guess[0] + '" class="guess">' + guess[1] + '</div>'); });
            $('#combobox_dropdown').html(guesses.join(' '));
            $(".guess").each(function(i, guess) {
                $(guess).click(function() {
                    $("#upload_form").append(
                        "<input type='hidden' id='file" + current_file +
                        "' name='spectrum' value='db:" + $(guess).attr('id') + "' />"
                    );
                    add_to_list($(this).html(), current_file);
                    $('#browse_dialog').hide();
                    // Move the file upload box to the next id.
                    file_upload = $("#file" + current_file);
                    current_file++;
                    file_upload.attr('id', 'file' + current_file);
                });
            });
            $('#combobox_dropdown').show(); //Finally, display it
        },
        'json'
    );
});

var current_file = 1;
function onchange_file() {
    if(this.value) {
        $(this).unbind("change");
        add_to_list(this.value.match('[^\\\\]+$'), current_file);
        $(this).hide();
        current_file++;
        $("#upload_form").append("<input type='file' class='invisible-frame' id='file" + current_file + "' name='spectrum' />")
        $("#file" + current_file).change(onchange_file);
        $("#file" + current_file).show()
    }
};

$(document).ready(function() {
    $('#upload_form').iframePostForm({
        complete: got_results
    });
    $("#upload_form").append("<input type='file' class='invisible-frame' id='file1' name='spectrum' />")
    $("#file1").change(onchange_file);
});

/**
 * jQuery plugin for posting form including file inputs.
 * Copyright (c) 2010 Ewen Elder
**/

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