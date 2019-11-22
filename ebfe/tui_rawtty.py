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

tty = lambda: None

class driver (tui.driver):
    def __init__ (self):
        tui.driver.__init__(self)

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

    # Returns a tuple containing the state of ALT/escape key and the translated input
    # wait for 0.1 seconds before returning None if no key was pressed
    def get_message (self):
        k = sys.stdin.read(1)
        if k == 'q':
            return tui.key_message(k)
        elif k == '\0x1b':
            return tui.key_message('Esc')
        elif len(k) > 0:
            return tui.key_message('Esc')
            #print("k({}): ".format(len(k)), end='')
            #for c in k:
            #    print('{0:X}, '.format(ord(c)), end='')
            #print("\r\n", end='')
        #time.sleep(1)
        else:
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
        self.move_to(column, row)
        print(text, end='')

    def prepare_render_text (self):
        pass

    def finish_render_text (self):
        pass

    def build_style (drv, style):
        return ''

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
        sys.stdout.write('\x1b[{};{}H'.format(y, x))

    def restore_state(self):
        self.show_cursor()
        if len(self.term_settings) > 0:
            termios.tcsetattr(self.stdin, termios.TCSAFLUSH, self.term_settings)


def sig_resize_func(signalnr, frame):
    #TODO fix this to send a message 
    if tty:
        rows, columns, *_ = struct.unpack('HHHH', fcntl.ioctl(sys.stdout.fileno(), termios.TIOCGWINSZ, struct.pack('HHHH', 0, 0, 0, 0)))
   

#return driver_runner(lambda drv, app = app: app.loop(drv))
def run (func):
    tty = driver()
    O['drv'] = tty
    signal.signal(signal.SIGWINCH, sig_resize_func)
    return func(tty)
    #return func(driver(stdscr))
