import ebfe.tui as tui
from zlx.io import dmsg

def main (tui_driver, cli):
    msg = tui_driver.get_message()

class title_bar (tui.window):
    '''
    Title bar
    '''
    def __init__ (self, title = ''):
        tui.window.__init__(self, title)
        self.title = title

    def refresh_strip (self, row, col, width):
        text = self.title[col : col + width].ljust(width)

        self.write(0, col, 'default', text)
        return

class editor (tui.application):
    '''
    This is the editor app.
    '''

    def __init__ (self, cli):
        tui.application.__init__(self)
        self.tick = 0
        self.title_bar = title_bar('ebfe - Exuberant Binary File Editor')

    def resize (self, width, height):
        self.width = width
        self.height = height
        self.title_bar.resize(width, 1)
        self.refresh()

    def refresh_strip (self, row, col, width):
        if row == 0:
            self.title_bar.refresh_strip(0, col, width)
            self.integrate_updates(0, 0, self.title_bar.fetch_updates())
            return
            
        if row == 1 and col == 0:
            self.write(1, 0, 'default', "|/-\\"[self.tick & 3])
            if width > 1:
                self.refresh_strip(1, 1, width - 1)
        else:
            tui.application.refresh_strip(self, row, col, width)

    def handle_timeout (self, msg):
        self.tick += 1
        self.refresh(
                start_row = 1,
                start_col = 0,
                height = 1,
                width = 1)

    def handle_char (self, msg):
        if msg.ch in ('q', '\x1B'): raise tui.app_quit(0)


