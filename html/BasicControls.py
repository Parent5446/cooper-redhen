'''
Basic controls widget for spectra comparison.
'''
from pyjamas.ui.RootPanel import RootPanel
from pyjamas.ui.ListBox import ListBox
from pyjamas.ui.FileUpload import FileUpload
from pyjamas import Window
from pyjamas import DOM
from pyjamas.ui.HTML import HTML
from pyjamas.ui.Button import Button
from pyjamas.ui.Grid import Grid
from pyjamas.ui.AbsolutePanel import AbsolutePanel
from pyjamas.ui.Image import Image
from pyjamas.ui.VerticalPanel import VerticalPanel
from pyjamas.ui.Composite import Composite
from pyjamas.ui import HasAlignment
from pyjamas.ui.DockPanel import DockPanel
from pyjamas.ui.DialogBox import DialogBox
from pyjamas.ui.AutoComplete import AutoCompleteTextBox
from pyjamas.HTTPRequest import HTTPRequest
from pyjamas.ui.FormPanel import FormPanel
from pyjamas.ui.Frame import Frame
from pyjamas.ui import Event
from __pyjamas__ import JS, doc

class BasicControls(Composite):
    def __init__(self, StyleName=None):
        Composite.__init__(self) #Superclass constructor
        panel = VerticalPanel() #Master panel for the widget
        panel.setHorizontalAlignment(HasAlignment.ALIGN_CENTER)
        size = ('250px', '4em') #Size of controls
        absolute = AbsolutePanel(Size=size, StyleName=StyleName) #Panel which contains the controls
        file_frame = Frame('../public/file_upload_frame.html', StyleName='invisible-frame') #File upload control (not visible)
        doc().file_loaded = lambda file: panel.add(HTML('<i>my computer: '+file+'</i>'))

        uploaded_files = {} #Table of uploaded files

        #Make list of 'browse' options:
        browse_list = ListBox(StyleName='listbox')
        map(browse_list.addItem, ['my computer', 'my projects', 'main library'])
        browse_list.addChangeListener(lambda: file_frame.setVisible(browse_list.getSelectedItemText()[0]=='my computer'))
        def browse(event):
            dialog = VerticalPanel(StyleName='browse-dialog', Size=size)
            dialog.setHorizontalAlignment(HasAlignment.ALIGN_CENTER)
            dialog.add(HTML('Enter a chemical name from '+browse_list.getSelectedItemText()[0]+':'))
            input = AutoCompleteTextBox()
            dialog.add(input)
            input.setCompletionItems(['methanol', 'ethanol', 'propanol', 'butanol', 'pentanol'])
            box = DialogBox()
            def done():
                if input.getText(): panel.add(HTML('<i>'+browse_list.getSelectedItemText()[0]+': '+input.getText()+'</i>'))
                box.hide()
            dialog.onClick = done
            dialog.add(Button("Done", dialog)) #Passes button clicks to dialog
            dialog.setWidth("100%")
            box.setWidget(dialog)
            box.setPopupPosition(absolute.getAbsoluteLeft(), absolute.getAbsoluteTop()-10)
            box.show()
        
        #Make list of 'compare' options:
        compare_list = ListBox(StyleName='listbox')
        map(compare_list.addItem, ['to main library', 'to my projects', 'to each other'])
        def compare(event):
            element = file_frame.getElement()
            panel.add(HTML( 'Result: "'+str(DOM.getNodeType(element))+'"' ) )
            #file_frame.setUrl('../public/file_upload_frame.html')
            #file = file_upload.getFilename()
            #if file not in uploaded_files: panel.add(HTML('<i>my computer: '+file+'</i>'))
            #uploaded_files[file] = True
            #file_upload_form.submit()
            
        #Make grid layout:
        grid = Grid(2, 2)
        grid.setWidget(0, 0, Button('<b>Browse</b>', browse, StyleName='button'))
        grid.setWidget(1, 0, Button('<b>Compare</b>', compare, StyleName='button'))
        grid.setWidget(0, 1, browse_list)
        grid.setWidget(1, 1, compare_list)
        absolute.add(grid)
        absolute.add(file_frame, '-177px', '3px') #This is a kludge (transparent file upload layered over a visible button)
        panel.add(absolute)
        self.initWidget(panel) #This panel becomes the center of the widget, and we're done
    