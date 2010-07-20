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

if __name__ == '__main__':
    panel = AbsolutePanel(StyleName='center-panel') #So contents can overlap
    grid = Grid(2, 2)
    file_upload = FileUpload(StyleName='file-upload')
    uploaded_files = {}

    browse_list = ListBox(StyleName='listbox')
    map(browse_list.addItem, ['my computer', 'my projects', 'main library'])
    browse_list.addChangeListener(lambda: file_upload.setVisible(browse_list.getSelectedItemText()[0]=='my computer'))
    def browse(event):
        RootPanel().add(HTML('Browse '+browse_list.getSelectedItemText()[0]))
    
    compare_list = ListBox(StyleName='listbox')
    map(compare_list.addItem, ['to main library', 'to my projects', 'to each other'])
    def compare(event):
        file = file_upload.getFilename()
        if file not in uploaded_files: RootPanel().add(HTML('<i>'+file+'</i>'))
        uploaded_files[file] = True
    
    grid.setWidget(0, 0, Button('<b>Browse</b>', browse, StyleName='button'))
    grid.setWidget(1, 0, Button('<b>Compare</b>', compare, StyleName='button'))
    grid.setWidget(0, 1, browse_list)
    grid.setWidget(1, 1, compare_list)
    panel.add(grid)
    panel.add(file_upload, '-100px', '5px')
    
    RootPanel().add(Image('banner.png'))
    RootPanel().add(panel)