import curses
import os
import time
import ebfe.tui as tui

class driver (tui.driver):
    def __init__ (self, scr):
        tui.driver.__init__(self)
        self.scr = scr
        self.scr.notimeout(False)
        self.scr.timeout(1)
        self.scr.nodelay(True)
        self.pair_seed = 1

    def get_message (self):
        key = self.scr.getch()
        if key == -1:
            time.sleep(1 / 10)
            return tui.message(name = 'timeout')

        elif key == curses.KEY_RESIZE:
            yx = self.scr.getmaxyx()
            return tui.resize_message(yx[1], yx[0])

        else:
            return tui.message(name = 'char', ch = chr(key))

    def get_screen_size (self):
        yx = self.scr.getmaxyx()
        return tui.screen_size(width = yx[1], height = yx[0])

    def get_style_caps (self):
        return tui.style_caps(
                attr = tui.A_BOLD,
                fg_count = curses.COLORS,
                bg_count = curses.COLORS,
                fg_default = 7,
                bg_default = 0)

    def render_text (self, text, style_name, column, row):
        try:
            self.scr.addstr(row, column, text, self.style_map[style_name])
        except curses.error:
            pass

    def build_style (drv, style):
        attr = curses.A_NORMAL
        if style.attr & tui.A_BOLD: attr |= curses.A_BOLD
        cp = drv.pair_seed
        drv.pair_seed += 1
        curses.init_pair(cp, style.fg, style.bg)
        return attr | curses.color_pair(cp)


def wrapped_run (stdscr, func):
    return func(driver(stdscr))

def run (func):
    os.environ.setdefault('ESCDELAY', '10')
    return curses.wrapper(wrapped_run, func)
