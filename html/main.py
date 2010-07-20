from pyjamas.ui.RootPanel import RootPanel
from pyjamas.ui.VerticalPanel import VerticalPanel
from pyjamas.ui.ListBox import ListBox
from pyjamas.ui.FileUpload import FileUpload
from pyjamas import Window
from pyjamas import DOM
from pyjamas.ui.HTML import HTML
from pyjamas.ui.Button import Button
from pyjamas.ui.Grid import Grid
from pyjamas.ui.AbsolutePanel import AbsolutePanel

if __name__ == '__main__':
    panel = AbsolutePanel(StyleName='center-panel')
    grid = Grid(2, 2)

    browse_list = ListBox(StyleName='listbox')
    map(browse_list.addItem, ['my computer', 'my projects', 'main library'])
    def browse_list_changed():
        if browse_list.getSelectedItemText()[0]=='my computer':
            file_upload.setVisible(True)
        else: file_upload.setVisible(False)
    browse_list.addChangeListener(browse_list_changed)
    def browse(event):
        RootPanel().add(HTML('Browse '+browse_list.getSelectedItemText()[0]))
    
    compare_list = ListBox(StyleName='listbox')
    map(compare_list.addItem, ['main library', 'my projects', 'each other'])
    def compare(event):
        RootPanel().add(HTML('Compare '+compare_list.getSelectedItemText()[0]))
    
    grid.setWidget(0, 0, Button('<b>Browse</b>', browse, StyleName='button'))
    grid.setWidget(1, 0, Button('<b>Compare</b>', compare, StyleName='button'))
    grid.setWidget(0, 1, browse_list)
    grid.setWidget(1, 1, compare_list)
    panel.add(grid)
    
    file_upload = FileUpload(StyleName='file-upload')
    panel.add(file_upload, '-100px', '5px')
    
    RootPanel().add(panel)