from pyjamas.ui.RootPanel import RootPanel
from pyjamas.ui.VerticalPanel import VerticalPanel
from pyjamas.ui.ListBox import ListBox
from pyjamas import Window

def browse(event):
    Window.alert(event.getSelectedItemText()[0])
    
def compare(event):
    Window.alert(event.getSelectedItemText()[0])

if __name__ == '__main__':
    panel = VerticalPanel(StyleName='compare-panel')
 
    browseList = ListBox()
    for item in ['spectra', 'my computer', 'my projects', 'main library']: browseList.addItem('Browse '+item)
    browseList.addChangeListener(browse)
    compareList = ListBox()
    for item in ['spectra', 'main library', 'my projects', 'each other']: compareList.addItem('Compare '+item)
    compareList.addChangeListener(compare)
    
    panel.add(browseList)
    panel.add(compareList)
    
    RootPanel().add(panel)