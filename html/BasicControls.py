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
from pyjamas.ui.TextBox import TextBox

class BasicControls(Composite):
    def __init__(self, StyleName=None):
        Composite.__init__(self) #Superclass constructor
        panel = VerticalPanel() #Master panel for the widget
        panel.setHorizontalAlignment(HasAlignment.ALIGN_CENTER)
        size = ('250px', '4em') #Size of controls
        absolute = AbsolutePanel(Size=size, StyleName=StyleName) #Panel which contains the controls
        file_upload = FileUpload(StyleName='file-upload') #File upload control (not visible)
        uploaded_files = {} #Table of uploaded files

        #Make list of 'browse' options:
        browse_list = ListBox(StyleName='listbox')
        map(browse_list.addItem, ['my computer', 'my projects', 'main library'])
        browse_list.addChangeListener(lambda: file_upload.setVisible(browse_list.getSelectedItemText()[0]=='my computer'))
        def browse(event):
            dialog = VerticalPanel(StyleName='browse-dialog', Size=size)
            dialog.setHorizontalAlignment(HasAlignment.ALIGN_CENTER)
            dialog.add(HTML('Enter a chemical name from '+browse_list.getSelectedItemText()[0]+':'))
            input = TextBox()
            options = ListBox()
            options.setVisibleItemCount(4)
            dialog.add(input)
            dialog.add(options)
            options.setVisible(False)
            def keyPressed(self, sender, keycode, modifiers):
                text = input.getText()
                if len(text) == 5:
                    map(options.addItem, ['methanol', 'ethanol', 'propanol', 'butanol', 'pentanol'])
                    options.setVisible(True)
                elif len(text) > 5:
                    options.addItem(text)
            box = DialogBox()
            def done():
                selected = options.getSelectedItemText()
                if selected:
                    panel.add(HTML('<i>'+browse_list.getSelectedItemText()[0]+': '+selected[0]+'</i>'))
                box.hide()
            dialog.onClick = done
            listener = object()
            listener.onKeyPress = lambda: None
            listener.onKeyUp = keyPressed
            listener.onKeyDown = lambda: None
            input.addKeyboardListener(listener)
            dialog.add(Button("Done", dialog)) #Passes button clicks to dialog
            dialog.setWidth("100%")
            box.setWidget(dialog)
            box.setPopupPosition(absolute.getAbsoluteLeft(), absolute.getAbsoluteTop()-10)
            box.show()
        
        #Make list of 'compare' options:
        compare_list = ListBox(StyleName='listbox')
        map(compare_list.addItem, ['to main library', 'to my projects', 'to each other'])
        def compare(event):
            file = file_upload.getFilename()
            if file not in uploaded_files: panel.add(HTML('<i>my computer: '+file+'</i>'))
            uploaded_files[file] = True
            
        #Make grid layout:
        grid = Grid(2, 2)
        grid.setWidget(0, 0, Button('<b>Browse</b>', browse, StyleName='button'))
        grid.setWidget(1, 0, Button('<b>Compare</b>', compare, StyleName='button'))
        grid.setWidget(0, 1, browse_list)
        grid.setWidget(1, 1, compare_list)
        absolute.add(grid)
        absolute.add(file_upload, '-100px', '5px') #This is a kludge (transparent file upload layered over a visible button)
        panel.add(absolute)
        self.initWidget(panel) #This panel becomes the center of the widget, and we're done
    