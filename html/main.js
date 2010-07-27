$(document).ready(function() {
    session_id = Math.floor(Math.random()*1e12)+(new Date()).getTime(); //Unique ID so the server can distinguish clients
});

function unload(file) {
    $('#checkbox_'+file).css('display', 'none');
    var action = function(response) { alert('Deleted '+file+' from server.'); };
    $.ajax({ url: '/api', success: action });
}

function add_to_list(s) {
    if( !s ) return;
    var id = String(s).replace('.','_');
    $('#loaded_list').html('<div id="checkbox_'+id+'"><input type="checkbox" checked="yes" onclick="unload(\''+id+'\');" />'+s+'</div>');
    $('#loaded_list').css('display', 'block');
}
 
function combobox_clicked(text) {
    $('#combobox_text').val(text);
    $('#combobox_dropdown').css('display', 'none');
    $('#combobox_text').focus();
}

$('#browse_button').click(function() {
    var selected = $('#browse_options option:selected').val();
    $('#browse_dialog').css('display', 'block');
    $('#combobox_text').focus();
});

function Spectrum(name, data, color) //Spectrum class
{
    this.name = name; this.data = data; this.color = color;
}

$('#compare_button').click(function() {
    var selected = $('#compare_options option:selected').val();
    $('#loaded_list').css('display', 'none');
    $('body').css('padding', '0px');
    $('#results').html('Getting results...');
    $('#graph').css('display', 'block');
    $('#results').css('display', 'block');
    var got_results = function(response) { //Once the server has responded
        $('#results').html(response); //List the spectra in the results bar
        var spectra = Array(); //Hold data
        spectra.push(new Spectrum('methanol', Array(), 'red'));
        spectra.push(new Spectrum('ethanol', Array(), 'blue'));
        spectra.push(new Spectrum('propanol', Array(), 'green'));
        var selected = 0;
        jQuery.each(spectra, function(i, spectrum) { //Make dummy values for testing
            for(var x=0; x<$('#graph').width(); x++) { 
                spectrum.data.push(Math.round( Math.sin(x/53.0517)*(50+50*i) )+150);
            }}); //Done with dummy values
        var vertical_divs = Array(); //Prepare the lines on the screen
        jQuery.each(spectra, function(i, spectrum) { //For each spectrum to be graphed
            for(var x=0; x<$('#graph').width(); x++) { //For each point in the spectrum
                var y = spectrum.data[x]; var oldy = y; if(x>0) oldy = spectrum.data[x-1]; //get the y data
                /*
                if(y>oldy) vertical_divs.push('<div class="graph-antialias" style="background-color:'+spectrum.color+'; left:'+x+'px; height:'+(y-oldy+2)+'px; bottom:'+(oldy-1)+'px;"></div>'); //Make an upward rectangle
                else if(y<oldy) vertical_divs.push('<div class="graph-antialias" style="background-color:'+spectrum.color+'; left:'+x+'px; height:'+(oldy-y+2)+'px; bottom:'+(y-1)+'px;"></div>'); //or make a downward rectangle
                else vertical_divs.push('<div class="graph-antialias" style="background-color:'+spectrum.color+'; left:'+x+'px; height:3px; bottom:'+(y-1)+'px;"></div>'); //or make a horizontal rectangle
                */
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
            $('#floatybar').css('display', 'block');
            $('#tracepoint').css('left', x-2);
            $('#tracepoint').css('bottom', spectra[selected].data[x]-2);
            $('#tracepoint').css('display', 'block');
        });
        $('#graph').click( function(e) {
            var x = Math.floor(e.pageX - $('#graph').position().left);
            var y = 300+$('#graph').position().top-e.pageY;
            for(var i in spectra) if(Math.abs(spectra[i].data[x]-y)<15) { selected=i; break; }
        });
        $('#graph').mouseout( function(e) {
            $('#floatybar').css('display', 'none');
            $('#tracepoint').css('display', 'none');
            document.body.style.cursor="default";
        });
    };
    $.ajax({ url: '/api', success: got_results });
});

$('#browse_options').change(function() {
    //Make file upload frame go away when not selected
    var selected = $('#browse_options option:selected').val();
    $('#file_frame').css('display', (selected=='my computer')?'block':'none');
});

$('#done_button').click(function() {
    $('#browse_dialog').css('display', 'none');
    add_to_list($('#combobox_text').val());
    $('#combobox_text').val('');
    $('#combobox_dropdown').css('display', 'none');
    $('#combobox_dropdown').html('');
});

$('#combobox_text').keyup(function(key) {
    var unicode = key.keyCode ? key.keyCode : key.charCode;
    if(unicode==13) $('#done_button').click();
    if($('#combobox_text').val().length<4) return;
    $('#combobox_dropdown').load( '/api', $('#combobox_text').val() )
    $('#combobox_dropdown').css('display', 'block');
});
