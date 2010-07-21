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
        Composite.__init__(self)
        panel = AbsolutePanel(Size=('250px', None), StyleName=StyleName)
        grid = Grid(2, 2)
        file_upload = FileUpload(StyleName='file-upload')
        uploaded_files = {}

        browse_list = ListBox(StyleName='listbox')
        map(browse_list.addItem, ['my computer', 'my projects', 'main library'])
        browse_list.addChangeListener(lambda: file_upload.setVisible(browse_list.getSelectedItemText()[0]=='my computer'))
        def browse(event):
            dialog = DialogBox()
            dock = DockPanel(StyleName='browse-dialog', Size=('250px', None))
            dock.setSpacing(4)
            dock.setHorizontalAlignment(HasAlignment.ALIGN_CENTER)
            dock.add(HTML('Enter a chemical name from '+browse_list.getSelectedItemText()[0]+':'), DockPanel.NORTH)
            input = TextBox()
            def keyPressed(self, sender, keycode, modifiers):
                text = input.getText()
                if len(text) == 5:
                    Window.alert('Looking up '+text)
                elif len(text) > 5:
                    Window.alert('Narrowing down '+text)
            def done():
                Window.alert( input.getText() )
                dialog.hide()
            dialog.onClick = done
            listener = object()
            listener.onKeyPress = lambda: None
            listener.onKeyUp = keyPressed
            listener.onKeyDown = lambda: None
            input.addKeyboardListener(listener)
            dock.add(input, DockPanel.CENTER)
            dock.add(Button("Done", dialog), DockPanel.SOUTH) #Passes button clicks to dialog
            dock.setWidth("100%")
            dialog.setWidget(dock)
            dialog.setPopupPosition(panel.getAbsoluteLeft(), panel.getAbsoluteTop()-10)
            dialog.show()
        
        compare_list = ListBox(StyleName='listbox')
        map(compare_list.addItem, ['to main library', 'to my projects', 'to each other'])
        def compare(event):
            file = file_upload.getFilename()
            if file not in uploaded_files: Window.alert(HTML('<i>'+file+'</i>'))
            uploaded_files[file] = True
            
        grid.setWidget(0, 0, Button('<b>Browse</b>', browse, StyleName='button'))
        grid.setWidget(1, 0, Button('<b>Compare</b>', compare, StyleName='button'))
        grid.setWidget(0, 1, browse_list)
        grid.setWidget(1, 1, compare_list)
        panel.add(grid)
        panel.add(file_upload, '-100px', '5px')
        
        self.initWidget(panel)

if __name__ == '__main__':
    dock = DockPanel(StyleName='centered-panel')
    dock.setHorizontalAlignment(HasAlignment.ALIGN_CENTER)
    dock.add(Image('banner.png'), DockPanel.NORTH)
    dock.add(BasicControls(StyleName='frontpage-controls'), DockPanel.CENTER)
    RootPanel().add(dock)
    