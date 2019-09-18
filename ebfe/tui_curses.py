import curses
import ebfe.tui

class driver (ebfe.tui.driver):
    def __init__ (self, scr):
        ebfe.tui.driver.__init__(self)
        self.scr = scr

    def get_message (self):
        return ebfe.tui.message('char', ch = self.scr.getch())

    def get_screen_size (self):
        yx = self.scr.getyx()
        return ebfe.tui.screen_size(width = yx[1], height = yx[0])


def wrapped_run (stdscr, opts, func):
    func(driver(stdscr), opts)

def run (opts, func):
    curses.wrapper(wrapped_run, opts, func)
