import os
import sys
import time
import traceback
import termios
import struct
import fcntl
import signal
import ebfe.tui as tui
from zlx.io import dmsg
from ebfe.interface import O

class driver (tui.driver):
    def __init__ (self):
        tui.driver.__init__(self)

        self.buffer = []

        self.resize_signal = False
        self.toggle = 'xx'

        self.stdout = sys.stdout.fileno()
        self.stdin = sys.stdin.fileno()
        self.term_settings = []
        try:
            self.term_settings = termios.tcgetattr(self.stdin)
        except:
            pass

        # If there are some settings then init the tty
        if len(self.term_settings) > 0:
            iflag, oflag, cflag, lflag, ispeed, ospeed, cc = self.term_settings
            # set no echo, no canonical mode, no CTRL_C, CTRL_Z, allow CTRL_V
            lflag &= 0xFFFFFFFF ^ (termios.ECHO | termios.ICANON | termios.ISIG | termios.IEXTEN)
            # set no CTRL_S, CTRL_Q, CTRL_M, CTRL_break, no parity checking, no 8th bit stripping
            iflag &= 0xFFFFFFFF ^ (termios.IXON | termios.ICRNL | termios.BRKINT | termios.INPCK | termios.ISTRIP)
            # set no line ending translation
            oflag &= 0xFFFFFFFF ^ (termios.OPOST)
            # set character size to 8 bits
            cflag |= termios.CS8

            # set console input timeout
            cc[termios.VMIN] = 0
            cc[termios.VTIME] = 1

            termios.tcsetattr(self.stdin, termios.TCSAFLUSH, [iflag, oflag, cflag, lflag, ispeed, ospeed, cc])

        self.hide_cursor()
        self.move_to(0, 0)

    # Returns a tuple containing the state of ALT/escape key and the translated input
    # wait for 0.1 seconds before returning None if no key was pressed
    def get_message (self):
        self.move_to(0, 0)
        if self.resize_signal:
            self.resize_signal = False
            rows, columns, *_ = struct.unpack('HHHH', fcntl.ioctl(self.stdout, termios.TIOCGWINSZ, struct.pack('HHHH', 0, 0, 0, 0)))
            return tui.resize_message(columns, rows)

        k = sys.stdin.read(1)
        if len(k) == 1:
            if k == '\x1b':
                return tui.key_message('Esc')
            return tui.key_message(k)

        elif len(k) > 1:
            return tui.key_message('Esc')

        else:
            print(self.toggle)
            if self.toggle == 'xx':
                self.toggle = 'OO'
            else:
                self.toggle = 'xx'
            return tui.message(name = 'timeout')

    def get_screen_size (self):
        rows, columns, *_ = struct.unpack('HHHH', fcntl.ioctl(self.stdout, termios.TIOCGWINSZ, struct.pack('HHHH', 0, 0, 0, 0)))
        return tui.screen_size(width = columns, height = rows)

    def get_style_caps (self):
        return tui.style_caps(
                attr = tui.A_BOLD,
                fg_count = 256,
                bg_count = 256,
                fg_default = 7,
                bg_default = 0)

    def render_text (self, text, style_name, column, row):
        self.buffer.append('\x1b[{};{}H'.format(row+1, column+1) + self.style_map[style_name] + text + '\x1b[0m')
        #self.move_to(column, row)
        #print(self.style_map[style_name], end='')
        #print(text, end='')

    def prepare_render_text (self):
        pass

    def finish_render_text (self):
        for l in self.buffer:
            print(l, end='')
        self.buffer = []

    def build_style (drv, style):
        seq = '\x1b['

        seq += str(style.fg + 30)
        seq += ';'
        seq += str(style.bg + 40)

        #if style.attr & tui.A_BOLD: 
        #    seq += ';1'
        #seq += ';2'
        seq += 'm'
        return seq

    def set_cursor (self, mode, row, col):
        self.cursor_mode = mode
        self.cursor_row = row
        self.cursor_col = col

    def cls (self):
        sys.stdout.write('\x1b[2J')

    def show_cursor (self):
        sys.stdout.write('\x1b[?25h')

    def hide_cursor (self):
        sys.stdout.write('\x1b[?25l')

    def move_to (self, x, y):
        #sys.stdout.write('\x1b[{};{}f'.format(y, x))
        print('\x1b[{};{}H'.format(y+1, x+1), end='')

    def restore_state(self):
        self.move_to(0, 0)
        self.cls()
        self.show_cursor()
        if len(self.term_settings) > 0:
            termios.tcsetattr(self.stdin, termios.TCSAFLUSH, self.term_settings)


def sig_resize_func(signalnr, frame):
    O['drv'].resize_signal = True
   

#return driver_runner(lambda drv, app = app: app.loop(drv))
def run (func):
    tty = driver()
    O['drv'] = tty
    signal.signal(signal.SIGWINCH, sig_resize_func)
    return func(tty)
    #return func(driver(stdscr))
