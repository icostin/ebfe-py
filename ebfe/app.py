# standard module imports
import datetime
import io

# custom external module imports
import zlx.io
from zlx.io import dmsg

# internal module imports
import ebfe.tui as tui


#* main *********************************************************************
def main (tui_driver, cli):
    msg = tui_driver.get_message()

#* open_file_from_uri *******************************************************
def open_file_from_uri (uri):
    if '://' in uri:
        scheme, res = uri.split('://', 1)
    else:
        scheme, res = 'file', uri
    if scheme == 'file':
        return open(res, 'rb')
    elif scheme == 'mem':
        return io.BytesIO()

#* title_bar ****************************************************************
class title_bar (tui.window):
    '''
    Title bar
    '''
    def __init__ (self, title = ''):
        tui.window.__init__(self, title)
        self.title = title
        self.tick = 0

    def refresh_strip (self, row, col, width):
        t = str(datetime.datetime.now())

        text = '[{}] {}'.format("|/-\\"[self.tick & 3], self.title)
        if len(text) + len(t) >= self.width:
            t = ''
        text = text.ljust(self.width - len(t))
        text += t

        self.write(0, col, 'normal_title', text[col : col + width])
        return

    def handle_timeout (self, msg):
        self.tick += 1
        self.refresh(start_row = 0, height = 1)

#* stream_edit_window *******************************************************
class stream_edit_window (tui.window):
    '''
    This is the window class for stream/file editing.
    '''

    def __init__ (win, stream_cache, stream_uri):
        tui.window.__init__(win)
        win.stream_uri = stream_uri
        win.stream_cache = stream_cache

    def refresh_strip (self, row, col, width):
        if row == 0:
            self.write(0, col, 'default', 'x' * width)
        else:
            tui.window.refresh_strip(self, row, col, width)


#* editor *******************************************************************
class editor (tui.application):
    '''
    This is the editor app (and the root window).
    '''

    def __init__ (self, cli):
        tui.application.__init__(self)
        self.tick = 0
        self.title_bar = title_bar('ebfe - Exuberant Binary File Editor')

        self.stream_windows = []
        if not cli.file:
            cli.file.append('mem://0')

        for uri in cli.file:
            f = open_file_from_uri(uri)
            sc = zlx.io.stream_cache(f)
            sew = stream_edit_window(
                    stream_cache = sc,
                    stream_uri = uri)
            self.stream_windows.append(sew)

        self.active_stream_index = 0
        self.active_stream_win = self.stream_windows[self.active_stream_index]
        return

    def generate_style_map (self, style_caps):
        sm = {}
        sm['default'] = tui.style(
                attr = tui.A_NORMAL,
                fg = style_caps.fg_default,
                bg = style_caps.bg_default)
        sm['normal_title'] = tui.style(attr = tui.A_NORMAL, fg = 1, bg = 7)
        return sm

    def resize (self, width, height):
        self.width = width
        self.height = height
        if width > 0 and height > 0: self.title_bar.resize(width, 1)
        if self.active_stream_win and width > 0 and height > 2:
            self.active_stream_win.resize(width, height - 2)
        if width > 0 and height > 0: self.refresh()

    def refresh_strip (self, row, col, width):
        if row == 0:
            self.title_bar.refresh_strip(0, col, width)
            self.integrate_updates(0, 0, self.title_bar.fetch_updates())
            return
        elif row >= 1 and row <= self.height - 1 and self.active_stream_win:
            self.active_stream_win.refresh_strip(row - 1, col, width)
            self.integrate_updates(1, 0, self.active_stream_win.fetch_updates())
        else:
            tui.application.refresh_strip(self, row, col, width)

    def handle_timeout (self, msg):
        self.title_bar.handle_timeout(msg)
        self.integrate_updates(0, 0, self.title_bar.fetch_updates())

    def handle_char (self, msg):
        if msg.ch in ('q', '\x1B'): raise tui.app_quit(0)


