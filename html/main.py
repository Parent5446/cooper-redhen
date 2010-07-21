'''
A spectra-comparison website, which compiles to Javascript via Pyjamas (version 0.7).
'''
from pyjamas.ui.RootPanel import RootPanel
from pyjamas.ui.Image import Image
from pyjamas.ui import HasAlignment
from pyjamas.ui.DockPanel import DockPanel

from BasicControls import BasicControls

if __name__ == '__main__':
    page = DockPanel(StyleName='centered-panel')
    page.setHorizontalAlignment(HasAlignment.ALIGN_CENTER)
    page.add(Image('../public/banner.png'), DockPanel.NORTH)
    page.add(BasicControls(StyleName='frontpage-controls'), DockPanel.CENTER)
    RootPanel().add(page)
    