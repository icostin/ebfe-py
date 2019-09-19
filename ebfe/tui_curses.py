import curses
import os
import time
import ebfe.tui

class driver (ebfe.tui.driver):
    def __init__ (self, scr):
        ebfe.tui.driver.__init__(self)
        self.scr = scr
        self.scr.notimeout(False)
        self.scr.timeout(1)
        self.scr.nodelay(True)

    def get_message (self):
        key = self.scr.getch()
        if key == -1:
            time.sleep(1 / 10)
            return ebfe.tui.message(name = 'timeout')

        elif key == curses.KEY_RESIZE:
            yx = self.scr.getmaxyx()
            return ebfe.tui.resize_message(yx[1], yx[0])

        else:
            return ebfe.tui.message(name = 'char', ch = chr(key))

    def get_screen_size (self):
        yx = self.scr.getmaxyx()
        return ebfe.tui.screen_size(width = yx[1], height = yx[0])

    def get_style_caps (self):
        return style_caps(
                attr = A_NORMAL,
                fg_count = curses.COLORS,
                bg_count = curses.COLORS,
                fg_default = 7,
                bg_default = 0)

    def render_text (self, text, style_name, column, row):
        try:
            self.scr.addstr(row, column, text)
        except curses.error:
            pass

def wrapped_run (stdscr, func):
    return func(driver(stdscr))

def run (func):
    os.environ.setdefault('ESCDELAY', '10')
    return curses.wrapper(wrapped_run, func)
