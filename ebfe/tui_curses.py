import curses
import ebfe.tui

class driver (ebfe.tui.driver):
    def __init__ (self, scr):
        ebfe.tui.driver.__init__(self)
        self.scr = scr

    def get_message (self):
        return ebfe.tui.message(name = 'char', ch = chr(self.scr.getch()))

    def get_screen_size (self):
        yx = self.scr.getyx()
        return ebfe.tui.resize_message(width = yx[1], height = yx[0])

    def render (self, updates):
        return

def wrapped_run (stdscr, func):
    return func(driver(stdscr))

def run (func):
    return curses.wrapper(wrapped_run, func)
