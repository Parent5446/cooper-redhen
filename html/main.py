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

class StartPage(Composite):
    def __init__(self):
        Composite.__init__(self)
        panel = AbsolutePanel(StyleName='start-control-panel')
        grid = Grid(2, 2)
        file_upload = FileUpload(StyleName='file-upload')
        uploaded_files = {}

        browse_list = ListBox(StyleName='listbox')
        map(browse_list.addItem, ['my computer', 'my projects', 'main library'])
        browse_list.addChangeListener(lambda: file_upload.setVisible(browse_list.getSelectedItemText()[0]=='my computer'))
        def browse(event):
            if browse_list.getSelectedItemText()[0] == 'my projects': pass
            elif browse_list.getSelectedItemText()[0] == 'main library': pass
        
        compare_list = ListBox(StyleName='listbox')
        map(compare_list.addItem, ['to main library', 'to my projects', 'to each other'])
        def compare(event):
            file = file_upload.getFilename()
            if file not in uploaded_files: self.add(HTML('<i>'+file+'</i>'))
            uploaded_files[file] = True
        
        grid.setWidget(0, 0, Button('<b>Browse</b>', browse, StyleName='button'))
        grid.setWidget(1, 0, Button('<b>Compare</b>', compare, StyleName='button'))
        grid.setWidget(0, 1, browse_list)
        grid.setWidget(1, 1, compare_list)
        panel.add(grid)
        panel.add(file_upload, '-100px', '5px')
        
        vertical = VerticalPanel()
        vertical.add(Image('banner.png'))
        vertical.add(panel)
        vertical.setHorizontalAlignment(HasAlignment.ALIGN_CENTER)
        vertical.setWidth("100%")
        self.initWidget(vertical)

if __name__ == '__main__':
    dp = DockPanel(StyleName='start-panel')
    dp.add(StartPage(), DockPanel.CENTER)
    RootPanel().add(dp)
    