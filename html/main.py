from pyjamas.ui.RootPanel import RootPanel
from pyjamas.ui.VerticalPanel import VerticalPanel
from pyjamas.ui.ListBox import ListBox
from pyjamas.ui.FileUpload import FileUpload
from pyjamas import Window
from pyjamas import DOM

def browse(event):
    if event.getSelectedItemText()[0] == "my computer":
        # Get the invisible file uploader and click it.
        file_upload = DOM.getElementById("file_upload")
        DOM.buttonClick(file_upload)
    else:
        Window.alert(event.getSelectedItemText()[0])
    
def compare(event):
    Window.alert(event.getSelectedItemText()[0])

if __name__ == '__main__':
    panel = VerticalPanel(StyleName='compare-panel')
 
    browse_list = ListBox()
    map(browse_list.addItem, ['spectra', 'my computer', 'my projects', 'main library'])
    browseList.addChangeListener(browse)
    
    compare_list = ListBox()
    map(compare_list.addItem, ['spectra', 'main library', 'my projects', 'each other'])
    compareList.addChangeListener(compare)
    
    file_upload = FileUpload()
    file_upload.setID("file_upload")
    file_upload.setVisible(False)
    
    panel.add(browse_list)
    panel.add(compare_list)
    panel.add(file_upload)
    RootPanel().add(panel)
