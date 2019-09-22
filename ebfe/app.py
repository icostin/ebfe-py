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
        tui.window.__init__(self, title,
            styles = '''
            passive_title
            normal_title
            dash_title
            time_title
            '''
        )
        self.title = title
        self.tick = 0

    def refresh_strip (self, row, col, width):
        t = str(datetime.datetime.now())

        stext = self.sfmt('{passive_title}[{dash_title}{}{passive_title}]{normal_title} {} ', "|/-\\"[self.tick & 3], self.title)
        #text = '[{}] {}'.format("|/-\\"[self.tick & 3], self.title)
        #if len(text) + len(t) >= self.width: t = ''
        stext_width = tui.compute_styled_text_width(stext)
        #dmsg('{!r} -> width {}', stext, stext_width)
        if stext_width + len(t) >= self.width:
            if stext_width < self.width:
                stext += self.sfmt('{passive_title}{}', ' ' * (self.width - stext_width))
        else:
            stext += self.sfmt('{passive_title}{}{time_title}{}', ' ' * (self.width - stext_width - len(t)), t)
        #text = text.ljust(self.width - len(t))
        #text += t


        #for style, text in tui.styled_text_chunks(stext, self.default_style_name):
        #    dmsg('chunk: style={!r} text={!r}', style, text)

        self.put(0, 0, stext, clip_col = col, clip_width = width)
        #self.put(0, col, text, [col : col + width])
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
        tui.window.__init__(self, styles='''
            default
            normal_offset offset_item_sep
            known_item uncached_item missing_item
            item1_sep item2_sep item4_sep item8_sep
            item_char_sep
            normal_char altered_char uncached_char missing_char
        ''')
        self.stream_uri = stream_uri
        self.stream_cache = stream_cache
        self.stream_offset = 0
        #self.offset_format = '{:+08X}: '
        self.items_per_line = 16

    def refresh_strip (self, row, col, width):
        row_offset = self.stream_offset + row * self.items_per_line
        #text = self.offset_format.format(row_offset)
        stext = self.sfmt('{normal_offset}{:+08X}{offset_item_sep}: ', row_offset)

        o = 0
        blocks = self.stream_cache.get(row_offset, self.items_per_line)
        #dmsg('got {!r}', blocks)
        cstrip = ''
        for blk in blocks:
            if blk.kind == zlx.io.SCK_HOLE:
                if blk.size == 0:
                    x = '{missing_item}  '
                    c = ' '
                    #x = '  '
                    #c = ' '
                    n = self.items_per_line - o
                else:
                    x = '{missing_item}--'
                    c = ' '
                    #c = ' '
                    n = blk.size
                stext += self.sfmt('{item1_sep} '.join((x for i in range(n))))
                #text += ' '.join((x for i in range(n)))
                cstrip += self.sfmt('{missing_char}{}', c * n)
            elif blk.kind == zlx.io.SCK_UNCACHED:
                #text += ' '.join(('??' for i in range(blk.size)))
                stext += self.sfmt('{item1_sep} '.join(('{uncached_item}??' for i in range(blk.size))))
                cstrip += self.sfmt('{uncached_char}?' * blk.size)
            elif blk.kind == zlx.io.SCK_CACHED:
                #text += ' '.join(('{:02X}'.format(b) for b in blk.data))
                #cstrip = ''.join((chr(b) if b >= 0x20 and b <= 0x7E else '.' for b in blk.data))
                stext += self.sfmt('{item1_sep} ').join((self.sfmt('{known_item}{:02X}', b) for b in blk.data))
                cstrip = ''.join((self.sfmt('{normal_char}{}', chr(b)) if b >= 0x20 and b <= 0x7E else self.sfmt('{altered_char}.') for b in blk.data))
            o += blk.get_size()
            #text += ' '
            stext += self.sfmt('{item1_sep} ')
        stext += self.sfmt('{item_char_sep} ') + cstrip
        #text += ' ' + cstrip
        #text = text.ljust(self.width)
        #self.write(row, 0, 'default', text, clip_col = col, clip_width = width)
        sw = tui.compute_styled_text_width(stext)
        stext += self.sfmt('{default}{}', ' ' * max(0, self.width  - sw))
        self.put(row, 0, stext, clip_col = col, clip_width = width)

    def vmove (self, count = 1):
        self.stream_offset += self.items_per_line * count
        self.refresh()

    def shift_offset (self, disp):
        self.stream_offset += disp
        self.refresh()

    def adjust_items_per_line (self, disp):
        self.items_per_line += disp
        if self.items_per_line < 1: self.items_per_line = 1
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
        # sm = {}
        # sm['default'] = tui.style(
        #         attr = tui.A_NORMAL,
        #         fg = style_caps.fg_default,
        #         bg = style_caps.bg_default)
        # sm['normal_title'] = tui.style(attr = tui.A_NORMAL, fg = 1, bg = 7)
        # sm['passive_title'] = tui.style(attr = tui.A_NORMAL, fg = 0, bg = 7)
        # sm['dash_title'] = tui.style(attr = tui.A_BOLD, fg = 2, bg = 7)
        # sm['time_title'] = tui.style(attr = tui.A_BOLD, fg = 4, bg = 7)
        # sm['normal_offset'] = tui.style(attr = tui.A_NORMAL, fg = 7, bg = 0)
        # sm['offset_item_sep'] = tui.style(attr = tui.A_NORMAL, fg = 6, bg = 0)
        # sm['known_item'] = tui.style(attr = tui.A_NORMAL, fg = 7, bg = 0)
        # sm['uncached_item'] = tui.style(attr = tui.A_NORMAL, fg = 4, bg = 0)
        # sm['missing_item'] = tui.style(attr = tui.A_NORMAL, fg = 8, bg = 0)
        # sm['item1_sep'] = tui.style(attr = tui.A_NORMAL, fg = 8, bg = 0)
        # sm['item2_sep'] = tui.style(attr = tui.A_NORMAL, fg = 8, bg = 0)
        # sm['item4_sep'] = tui.style(attr = tui.A_NORMAL, fg = 8, bg = 0)
        # sm['item8_sep'] = tui.style(attr = tui.A_NORMAL, fg = 8, bg = 0)
        # sm['item_char_sep'] = tui.style(attr = tui.A_NORMAL, fg = 8, bg = 0)
        # sm['normal_char'] = tui.style(attr = tui.A_NORMAL, fg = 6, bg = 0)
        # sm['altered_char'] = tui.style(attr = tui.A_NORMAL, fg = 8, bg = 0)
        # sm['uncached_char'] = tui.style(attr = tui.A_NORMAL, fg = 12, bg = 0)
        # sm['missing_char'] = tui.style(attr = tui.A_NORMAL, fg = 8, bg = 0)
        sm = tui.parse_styles(style_caps, '''
            default attr=normal fg=7 bg=0
            normal_title attr=normal fg=1 bg=7
            passive_title attr=normal fg=0 bg=7
            dash_title attr=bold fg=2 bg=7
            time_title attr=bold fg=4 bg=7
            normal_offset attr=normal fg=7 bg=0
            offset_item_sep attr=normal fg=6 bg=0
            known_item attr=normal fg=7 bg=0
            uncached_item attr=normal fg=4 bg=0
            missing_item attr=normal fg=8 bg=0
            item1_sep attr=normal fg=8 bg=0
            item2_sep attr=normal fg=8 bg=0
            item4_sep attr=normal fg=8 bg=0
            item8_sep attr=normal fg=8 bg=0
            item_char_sep attr=normal fg=8 bg=0
            normal_char attr=normal fg=6 bg=0
            altered_char attr=normal fg=8 bg=0
            uncached_char attr=normal fg=12 bg=0
            missing_char attr=normal fg=8 bg=0
            ''')
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
        elif msg.ch[1] in ('<',): self.act('shift_offset', -1)
        elif msg.ch[1] in ('>',): self.act('shift_offset', +1)
        elif msg.ch[1] in ('-',): self.act('adjust_items_per_line', -1)
        elif msg.ch[1] in ('+',): self.act('adjust_items_per_line', +1)
        elif msg.ch[1] in ('\x06',): self.act('vmove', self.height - 3) # Ctrl-F
        elif msg.ch[1] in ('\x02',): self.act('vmove', -(self.height - 3)) # Ctrl-B
        elif msg.ch[1] in ('\x04',): self.act('vmove', self.height // 3) # Ctrl-D
        elif msg.ch[1] in ('\x15',): self.act('vmove', -(self.height // 3)) # Ctrl-U
        else:
            dmsg("Unknown key: {}", msg.ch)
