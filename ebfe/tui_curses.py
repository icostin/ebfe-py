import curses
import os
import time
import traceback
import ebfe.tui as tui
from zlx.io import dmsg

class driver (tui.driver):
    def __init__ (self, scr):
        tui.driver.__init__(self)
        self.scr = scr
        self.scr.clear()
        self.scr.refresh()
        #self.scr.notimeout(False)
        #self.scr.timeout(1000)
        self.scr.nodelay(True)
        curses.curs_set(0)
        self.pair_seed = 1

    # Returns a tuple containing the state of ALT/escape key and the translated input
    # wait for 0.1 seconds before returning None if no key was pressed
    def get_message (self):
        esc = False
        curses.halfdelay(1)
        
        try:
            #c = self.scr.getkey()
            c = self.scr.getkey()

            if c == 'KEY_RESIZE':
                yx = self.scr.getmaxyx()
                return tui.resize_message(yx[1], yx[0])
            
            elif c == '\t':
                return tui.message(name = 'key', key = 'Tab')
            elif c == '\n':
                return tui.message(name = 'key', key = 'Enter')

            elif c == '\x0c':
                self.scr.clear()
                return tui.message(name = 'key', key = 'Ctrl-L')

            elif c.startswith('KEY_F('):
                return tui.message(name = 'key', key = 'F' + c[6:-1])

            elif ord(c[0]) < 32:
                return tui.message(name = 'key', key = 'Ctrl-' + chr(ord(c[0]) + 64))

            # is it ESC or ALT+KEY ?
            elif c == '\x1b':
                esc = True
                c = self.scr.getkey()
                return tui.message(name = 'key', key = 'Alt-' + c)
            return tui.message(name = 'key', key = c)

        except curses.error as e:
            #self.scr.addstr(22, 0, '{}'.format(curses.error))
            #dmsg('exc: {}', traceback.format_exc())
            if esc:
                return tui.message(name = 'key', key = 'Esc')
            else:
                return tui.message(name = 'timeout')

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
