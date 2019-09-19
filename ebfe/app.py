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

    def handle_char (self, msg):
        dmsg('char: {!r}', msg.ch)
        if msg.ch == 'q': raise ebfe.tui.app_quit(0)


