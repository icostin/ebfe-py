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
        curses.curs_set(tui.CM_INVISIBLE)
        self.pair_seed = 1
        self.cursor_mode = tui.CM_INVISIBLE
        self.cursor_row = 0
        self.cursor_col = 0

    # Returns a tuple containing the state of ALT/escape key and the translated input
    # wait for 0.1 seconds before returning None if no key was pressed
    def get_message (self):
        esc = False
        curses.halfdelay(1)

        try:
            #c = self.scr.getkey()
            c = self.scr.getkey()
            dmsg('got key: {}', c)

            if c == 'KEY_RESIZE':
                yx = self.scr.getmaxyx()
                return tui.resize_message(yx[1], yx[0])

            elif c == '\0':
                return tui.key_message('Ctrl-Space')
            elif c == '\t':
                return tui.key_message('Tab')
            elif c == '\n':
                return tui.key_message('Enter')
            elif c == '\x0C':
                self.scr.clear()
                return tui.key_message('Ctrl-L')
            elif c.startswith('KEY_F('):
                return tui.key_message('F' + c[6:-1])
            elif c.startswith('KEY_'):
                return tui.key_message(c[4:].capitalize())
            # is it ESC or ALT+KEY ?
            elif c == '\x1b':
                esc = True
                c = self.scr.getkey()
                dmsg('continuation key: {}', c)
                return tui.key_message('Alt-' + c)
            elif ord(c[0]) < 32:
                return tui.key_message('Ctrl-' + chr(ord(c[0]) + 64))
            return tui.key_message(c)

        except curses.error as e:
            #self.scr.addstr(22, 0, '{}'.format(curses.error))
            #dmsg('exc: {}', traceback.format_exc())
            if esc:
                return tui.key_message('Esc')
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
            self.scr.noutrefresh()
        except curses.error:
            pass

    def prepare_render_text (self):
        self.scr.noutrefresh()
        self.scr.leaveok(True)

    def finish_render_text (self):
        curses.doupdate()
        self.scr.leaveok(False)
        curses.curs_set(self.cursor_mode)
        self.scr.move(self.cursor_row, self.cursor_col)

    def build_style (drv, style):
        attr = curses.A_NORMAL
        if style.attr & tui.A_BOLD: attr |= curses.A_BOLD
        cp = drv.pair_seed
        drv.pair_seed += 1
        curses.init_pair(cp, style.fg, style.bg)
        return attr | curses.color_pair(cp)

    def set_cursor (self, mode, row, col):
        self.cursor_mode = mode
        self.cursor_row = row
        self.cursor_col = col
        return

def wrapped_run (stdscr, func):
    return func(driver(stdscr))

def run (func):
    os.environ.setdefault('ESCDELAY', '10')
    return curses.wrapper(wrapped_run, func)
