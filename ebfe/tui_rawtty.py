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
            #lflag = 35377
            lflag &= 0xFFFFFFFF ^ (termios.ECHO | termios.ICANON | termios.ISIG | termios.IEXTEN | termios.ECHONL)
            # set no CTRL_S, CTRL_Q, CTRL_M, CTRL_break, no parity checking, no 8th bit stripping
            #iflag = 17408
            iflag &= 0xFFFFFFFF ^ (termios.IXON | termios.ICRNL | termios.BRKINT | termios.INPCK | termios.ISTRIP | termios.IGNBRK | termios.PARMRK | termios.INLCR | termios.IGNCR)
            # set no line ending translation
            #oflag = 1
            oflag &= 0xFFFFFFFF ^ (termios.OPOST)
            # set character size to 8 bits
            cflag &= 0xFFFFFFFF ^ (termios.CSIZE | termios.PARENB)
            cflag |= termios.CS8

            # set console input timeout
            cc[termios.VMIN] = 0
            cc[termios.VTIME] = 1

            #cc = [b'\x03', b'\x1c', b'\x7f', b'\x15', b'\x04', 0, 1, b'\x00', b'\x11', b'\x13', b'\x1a', b'\x00', b'\x12', b'\x0f', b'\x17', b'\x16', b'\x00', b'\x00', b'\x00', b'\x00', b'\x00', b'\x00', b'\x00', b'\x00', b'\x00', b'\x00', b'\x00', b'\x00', b'\x00', b'\x00', b'\x00', b'\x00']

            termios.tcsetattr(self.stdin, termios.TCSANOW, [iflag, oflag, cflag, lflag, ispeed, ospeed, cc])
        #---------------- CURSES PARAMS -------------
        # iflag: 17408
        # oflag: 1
        # cflag: 191
        # lflag: 35377
        # ispeed: 15
        # ospeed: 15
        # cc: [b'\x03', b'\x1c', b'\x7f', b'\x15', b'\x04', 0, 1, b'\x00', b'\x11', b'\x13', b'\x1a', b'\x00', b'\x12', b'\x0f', b'\x17', b'\x16', b'\x00', b'\x00', b'\x00', b'\x00', b'\x00', b'\x00', b'\x00', b'\x00', b'\x00', b'\x00', b'\x00', b'\x00', b'\x00', b'\x00', b'\x00', b'\x00']
        dmsg("*** iflag: {}", iflag)
        dmsg("*** oflag: {}", oflag)
        dmsg("*** cflag: {}", cflag)
        dmsg("*** lflag: {}", lflag)
        dmsg("*** ispeed: {}", ispeed)
        dmsg("*** ospeed: {}", ospeed)
        dmsg("*** cc: {}", cc)
        #----------------- RAW params from here ------------
        # iflag: 16384
        # oflag: 4
        # cflag: 191
        # lflag: 2608
        # ispeed: 15
        # ospeed: 15
        # cc: [b'\x03', b'\x1c', b'\x7f', b'\x15', b'\x04', 1, 0, b'\x00', b'\x11', b'\x13', b'\x1a', b'\x00', b'\x12', b'\x0f', b'\x17', b'\x16', b'\x00', b'\x00', b'\x00', b'\x00', b'\x00', b'\x00', b'\x00', b'\x00', b'\x00', b'\x00', b'\x00', b'\x00', b'\x00', b'\x00', b'\x00', b'\x00']

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
        dmsg("_______________INPUT k({}): {}", len(k), k)
        if len(k) == 1:
            if k == '\x1b':
                return tui.key_message('Esc')
            if k == '\x0d':
                return tui.key_message('Enter')
            return tui.key_message(k)

        elif len(k) > 1:
            return tui.key_message('Esc')

        #print(self.toggle)
        #if self.toggle == 'xx':
        #    self.toggle = 'OO'
        #else:
        #    self.toggle = 'xx'
        #sys.stdout.flush()
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
        self.buffer.append('\x1b[{};{}H'.format(row+1, column+1) + self.style_map[style_name] + text)
        #self.buffer.append('\x1b[{};{}H'.format(row+1, column+1) + self.style_map[style_name] + text + '\x1b[0m')
        #self.move_to(column, row)
        #print(self.style_map[style_name], end='')
        #print(text, end='')

    def prepare_render_text (self):
        pass

    def finish_render_text (self):
        for l in self.buffer:
            sys.stdout.write(l)
            #print(l, flush=True)
        sys.stdout.flush()
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
        sys.stdout.flush()

    def show_cursor (self):
        sys.stdout.write('\x1b[?25h')
        sys.stdout.flush()

    def hide_cursor (self):
        sys.stdout.write('\x1b[?25l')
        sys.stdout.flush()

    def move_to (self, x, y):
        sys.stdout.write('\x1b[{};{}H'.format(y+1, x+1))
        sys.stdout.flush()

    def restore_state(self):
        self.move_to(0, 0)
        self.cls()
        self.show_cursor()
        if len(self.term_settings) > 0:
            termios.tcsetattr(self.stdin, termios.TCSANOW, self.term_settings)


def sig_resize_func(signalnr, frame):
    O['drv'].resize_signal = True
   

#return driver_runner(lambda drv, app = app: app.loop(drv))
def run (func):
    tty = driver()
    O['drv'] = tty
    signal.signal(signal.SIGWINCH, sig_resize_func)
    return func(tty)
    #return func(driver(stdscr))
