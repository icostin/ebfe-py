# standard module imports
import datetime
import io

# custom external module imports
import zlx.io

# internal module imports
import ebfe.tui as tui

dlog = open('/tmp/ebfe.log', 'w')
def dmsg (f, *a, **b):
    dlog.write((f + '\n').format(*a, **b))

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
        f = io.BytesIO()
        f.write(b'All your bytes are belong to Us:' + bytes(i for i in range(256)))
        return f

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
        #self.refresh(start_row = 0, height = 1)
        self.refresh(start_row = 0, start_col = 1, height = 1, width = 1)
        self.refresh(start_row = 0, height = 1, start_col = self.width // 2)

#* stream_edit_window *******************************************************
class stream_edit_window (tui.window):
    '''
    This is the window class for stream/file editing.
    '''

    def __init__ (self, stream_cache, stream_uri):
        tui.window.__init__(self)
        self.stream_uri = stream_uri
        self.stream_cache = stream_cache
        self.stream_offset = 0
        self.offset_format = '{:+08X}: '
        self.items_per_line = 16

    def refresh_strip (self, row, col, width):
        row_offset = self.stream_offset + row * self.items_per_line
        text = self.offset_format.format(row_offset)
        o = 0
        blocks = self.stream_cache.get(row_offset, self.items_per_line)
        dmsg('got {!r}', blocks)
        cstrip = ''
        for blk in blocks:
            if blk.kind == zlx.io.SCK_HOLE:
                if blk.size == 0:
                    x = '  '
                    c = ' '
                    n = self.items_per_line - o
                else:
                    x = '--'
                    c = ' '
                    n = blk.size
                text += ' '.join((x for i in range(n)))
                cstrip += c * n
            elif blk.kind == zlx.io.SCK_UNCACHED:
                text += ' '.join(('??' for i in range(blk.size)))
                cstrip += '?' * blk.size
            elif blk.kind == zlx.io.SCK_CACHED:
                text += ' '.join(('{:02X}'.format(b) for b in blk.data))
                cstrip = ''.join((chr(b) if b >= 0x20 and b <= 0x7E else '.' for b in blk.data))
            o += blk.get_size()
            text += ' '
        text += ' ' + cstrip
        text = text.ljust(self.width)
        self.write(row, 0, 'default', text, clip_col = col, clip_width = width)

    def vmove (self, count = 1):
        self.stream_offset += self.items_per_line * count
        self.refresh()


#* editor *******************************************************************
class editor (tui.application):
    '''
    This is the editor app (and the root window).
    '''

    def __init__ (self, cli):
        tui.application.__init__(self)
        self.tick = 0
        self.title_bar = title_bar('ebfe - Exuberant Binary File Editor')
        self.mode = 'normal' # like vim normal mode

        self.stream_windows = []
        if not cli.file:
            cli.file.append('mem://0')

        for uri in cli.file:
            f = open_file_from_uri(uri)
            sc = zlx.io.stream_cache(f, align = 4)
            sc.load(0, sc.blocks[len(sc.blocks) - 1].offset // 2)
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
        elif row >= 1 and row < self.height - 1 and self.active_stream_win:
            self.active_stream_win.refresh_strip(row - 1, col, width)
            self.integrate_updates(1, 0, self.active_stream_win.fetch_updates())
        else:
            tui.application.refresh_strip(self, row, col, width)

    def handle_timeout (self, msg):
        self.title_bar.handle_timeout(msg)
        self.integrate_updates(0, 0, self.title_bar.fetch_updates())

    def act (self, func, *l, **kw):
        if self.active_stream_win:
            getattr(self.active_stream_win, func)(*l, **kw)
            self.integrate_updates(1, 0, self.active_stream_win.fetch_updates())

    def handle_keystate (self, msg):
        if msg.ch[1] in ('q', 'Q', 'ESC'): raise tui.app_quit(0)
        elif msg.ch[1] in ('j', 'J'): self.act('vmove', 1)
        elif msg.ch[1] in ('k', 'K'): self.act('vmove', -1)
        elif msg.ch[1] in ('\x06',): self.act('vmove', self.height - 2)
        elif msg.ch[1] in ('\x02',): self.act('vmove', -(self.height - 2))
        else:
            dmsg("Unknown key: {}", msg.ch)
