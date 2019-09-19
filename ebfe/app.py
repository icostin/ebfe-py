import ebfe.tui
from zlx.io import dmsg

def main (tui_driver, cli):
    msg = tui_driver.get_message()

class editor (ebfe.tui.app):
    '''
    This is the editor app.
    '''

    def __init__ (self, cli):
        ebfe.tui.app.__init__(self)
        self.tick = 0

    def refresh_strip (self, row, col, width):
        if row == 0 and col == 0:
            self.write(0, 0, 'default', "|\\-/"[self.tick & 3])
            if width > 1:
                self.refresh_strip(0, 1, width - 1)
        else:
            ebfe.tui.app.refresh_strip(self, row, col, width)

    def handle_timeout (self, msg):
        self.tick += 1
        self.refresh(
                start_row = 0,
                start_col = 0,
                height = 1,
                width = 1)

    def handle_char (self, msg):
        if msg.ch in ('q', '\x1B'): raise ebfe.tui.app_quit(0)


