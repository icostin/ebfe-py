# standard module imports
import datetime
import io
import os
import ebfe

# custom external module imports
import zlx.io
import configparser
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
        f = io.BytesIO()
        f.write(b'All your bytes are belong to Us:' + bytes(i for i in range(256)))
        return f

#* config class *************************************************************
class settings_manager ():

    def __init__ (self, cfg_file):
        self.cfg_file = cfg_file
        self.cfg = configparser.ConfigParser()
        #cfg_file = os.path.expanduser(cfg_file)
        # if config file exists it is parsed
        if os.path.isfile(cfg_file):
            self.cfg.read(cfg_file)
        # if not, it's created with the sections
        else:
            self.cfg['main settings'] = {}
            self.cfg['window: hex edit'] = {}
            self.save()

    def get (self, section, item, default):
        if section in self.cfg:
            return self.cfg[section].get(item, fallback=default)

    def set (self, section, item, value):
        if section not in self.cfg:
            self.cfg[section] = {}
        self.cfg.set(section, item, str(value))
        self.save()

    # gets the value and converts it to an int
    def iget (self, section, item, default):
        if section in self.cfg:
            return self.cfg[section].getint(item, fallback=default)

    # gets the value and converts it to a float
    def fget (self, section, item, default):
        if section in self.cfg:
            return self.cfg[section].getfloat(item, fallback=default)

    # gets the value and converts it to a bool
    def bget (self, section, item, default):
        if section in self.cfg:
            return self.cfg[section].getboolean(item, fallback=default)

    def save (self):
        with open(self.cfg_file, 'w') as cfg_file_handle:
            self.cfg.write(cfg_file_handle)

#* title_bar ****************************************************************
class title_bar (tui.window):
    '''
    Title bar
    '''
    def __init__ (self, title = ''):
        tui.window.__init__(self,
            wid = 'title_bar',
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

        stext = self.sfmt('{passive_title}[{dash_title}{}{passive_title}]{normal_title} {} - ver {} ', "|/-\\"[self.tick & 3], self.title, ebfe.VER_STR)
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

    def on_input_timeout (self):
        self.tick += 1
        #self.refresh(start_row = 0, height = 1)
        self.refresh(start_row = 0, start_col = 1, height = 1, width = 1)
        self.refresh(start_row = 0, height = 1, start_col = self.width // 2)

#* status_bar ****************************************************************
class status_bar (tui.window):
    '''
    Status bar
    '''
    def __init__ (self, title = ''):
        tui.window.__init__(self,
            wid = 'status_bar',
            styles = '''
            default_status_bar
            '''
        )
        self.title = title
        self.tick = 0

    def refresh_strip (self, row, col, width):
        dmsg('{}.refresh_strip(row={}, col={}, width={})', self, row, col, width)
        stext = self.sfmt('{default_status_bar}Status bar | Test:{}', ' ' * self.width)
        if row != 0:
            raise RuntimeError('boo')
        self.put(0, 0, stext, clip_col = col, clip_width = width)

#* job details **************************************************************
class processing_details (tui.window):
    '''
    Processing Job details
    '''
    def __init__ (self):
        tui.window.__init__(self,
            wid = 'processing_details_win',
            styles = '''
            default_status_bar
            '''
        )
        self.lines_to_display = 1

    def refresh_strip (self, row, col, width):
        stext = self.sfmt('{default_status_bar}Working...{}', ' ' * (self.width - 10))
        self.put(row, 0, stext, clip_col = col, clip_width = width)
        if self.in_focus and row == 0:
            dmsg("processing_details - ADD FOCUS CHAR TO THE UPDATE LIST")
            self.write_(0, 0, 'test_focus', '*')


#* console ******************************************************************
class console (tui.window):
    '''
    Console for commands
    '''
    def __init__ (self):
        tui.window.__init__(self,
            wid = 'console',
            styles = '''
            normal
            ''',
            can_have_focus = True
        )
        self.lines_to_display = 8
        self.on_focus_leave()

    def refresh_strip (self, row, col, width):
        stext = self.sfmt('{normal}{}:{}', row, ' ' * self.width)
        self.put(row, 0, stext, clip_col = col, clip_width = width)
        if self.in_focus and row == 0:
            dmsg("console - ADD FOCUS CHAR TO THE UPDATE LIST")
            self.write_(0, 0, 'test_focus', '*')

    def on_focus_enter (self):
        self.set_styles('''
            normal=active_console
        ''')
        self.refresh()

    def on_focus_leave (self):
        self.set_styles('''
            normal=inactive_console
        ''')
        self.refresh()



#* stream_edit_window *******************************************************
class stream_edit_window (tui.window):
    '''
    This is the window class for stream/file editing.
    '''

    def __init__ (self, stream_cache, stream_uri):
        tui.window.__init__(self, can_have_focus = True)
        cfg = settings_manager(os.path.expanduser('~/.ebfe.ini'))
        self.stream_uri = stream_uri
        self.stream_cache = stream_cache
        self.stream_offset = 0
        #self.offset_format = '{:+08X}: '
        self.items_per_line = cfg.iget('window: hex edit', 'items_per_line', 16)
        self.prev_items_per_line = self.items_per_line
        self.column_size = cfg.iget('window: hex edit', 'column_size', 4)
        self.fluent_scroll = cfg.bget('window: hex edit', 'fluent_scroll', True)
        self.fluent_resize = cfg.bget('window: hex edit', 'fluent_resize', True)
        self.reverse_offset_slide = cfg.bget('window: hex edit', 'reverse_offset_slide', True)
        self.refresh_on_next_tick = False
        self.show_hex = True

    def prepare_styles (self):
        if self.in_focus:
            self.set_styles('''
                default=active_default
                normal_offset=active_normal_offset
                negative_offset=active_negative_offset
                offset_item_sep=active_offset_item_sep
                known_item=active_known_item
                uncached_item=active_uncached_item
                missing_item=active_missing_item
                item1_sep=active_item1_sep
                item2_sep=active_item2_sep
                item4_sep=active_item4_sep
                item8_sep=active_item8_sep
                item_char_sep=active_item_char_sep
                normal_char=active_normal_char
                altered_char=active_altered_char
                uncached_char=active_uncached_char
                missing_char=active_missing_char
            ''')
        else:
            self.set_styles('''
                default=default
                normal_offset=inactive_normal_offset
                negative_offset=inactive_negative_offset
                offset_item_sep=inactive_offset_item_sep
                known_item=inactive_known_item
                uncached_item=inactive_uncached_item
                missing_item=inactive_missing_item
                item1_sep=inactive_item1_sep
                item2_sep=inactive_item2_sep
                item4_sep=inactive_item4_sep
                item8_sep=inactive_item8_sep
                item_char_sep=inactive_item_char_sep
                normal_char=inactive_normal_char
                altered_char=inactive_altered_char
                uncached_char=inactive_uncached_char
                missing_char=inactive_missing_char
            ''')


    def refresh_strip (self, row, col, width):
        row_offset = self.stream_offset + row * self.items_per_line
        #text = self.offset_format.format(row_offset)
        if row_offset < 0:
            stext = self.sfmt('{negative_offset}{:+08X}: ', row_offset)
        else:
            stext = self.sfmt('{normal_offset}{:+08X}{offset_item_sep}: ', row_offset)

        o = 0
        blocks = self.stream_cache.get(row_offset, self.items_per_line)
        #dmsg('got {!r}', blocks)
        cstrip = ''
        last_cstrip_style = '{normal}'
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
                #stext += self.sfmt('{item1_sep} '.join((x for i in range(n))))
                if self.show_hex:
                    for i in range(n):
                        if i+o != 0:
                            stext += self.sfmt('{item1_sep} ')
                            if self.column_size != 0 and ((i+o) % self.column_size) == 0:
                                stext += ' '
                        stext += self.sfmt(x)
                #text += ' '.join((x for i in range(n)))
                last_cstrip_style = '{missing_char}'
                cstrip += self.sfmt(last_cstrip_style + '{}', c * n)
            elif blk.kind == zlx.io.SCK_UNCACHED:
                #text += ' '.join(('??' for i in range(blk.size)))
                #stext += self.sfmt('{item1_sep} '.join(('{uncached_item}??' for i in range(blk.size))))
                if self.show_hex:
                    for i in range(blk.size):
                        if i+o != 0:
                            stext += self.sfmt('{item1_sep} ')
                            if self.column_size != 0 and ((i+o) % self.column_size) == 0:
                                stext += ' '
                        stext += self.sfmt('{uncached_item}??')

                last_cstrip_style = '{uncached_char}'
                cstrip += self.sfmt(last_cstrip_style + '?' * blk.size)
            elif blk.kind == zlx.io.SCK_CACHED:
                #text += ' '.join(('{:02X}'.format(b) for b in blk.data))
                #cstrip = ''.join((chr(b) if b >= 0x20 and b <= 0x7E else '.' for b in blk.data))
                #stext += self.sfmt('{item1_sep} ').join((self.sfmt('{known_item}{:02X}', b) for b in blk.data))
                i = 0
                for b in blk.data:
                    if self.show_hex:
                        if i + o != 0:
                            stext += self.sfmt('{item1_sep} ')
                            if self.column_size != 0 and ((i+o) % self.column_size) == 0:
                                stext += ' '
                        stext += self.sfmt('{known_item}{:02X}', b)

                    if b >= 0x20 and b <= 0x7E:
                        cstrip_style = '{normal_char}'
                        ch = chr(b)
                    else:
                        cstrip_style = '{altered_char}'
                        if b == 0: ch = '.'
                        elif b == 0xFF: ch = '#'
                        else: ch = '_'
                    if cstrip_style != last_cstrip_style:
                        cstrip += self.sfmt(cstrip_style)
                        last_cstrip_style = cstrip_style
                    cstrip += ch
                    i += 1
                #cstrip += ''.join((self.sfmt('{normal_char}{}', chr(b)) if b >= 0x20 and b <= 0x7E else self.sfmt('{altered_char}.') for b in blk.data))
            o += blk.get_size()
            #text += ' '
            #stext += self.sfmt('{item1_sep} ')
        if self.show_hex: stext += self.sfmt('{item_char_sep}  ')
        stext += cstrip
        #text += ' ' + cstrip
        #text = text.ljust(self.width)
        #self.write(row, 0, 'default', text, clip_col = col, clip_width = width)
        sw = tui.compute_styled_text_width(stext)
        stext += self.sfmt('{default}{}', ' ' * max(0, self.width  - sw))
        self.put(row, 0, stext, clip_col = col, clip_width = width)
        if self.in_focus and row == 0:
            dmsg("hex window - ADD FOCUS CHAR TO THE UPDATE LIST, self: {}, focus: {}, height: {}", self, self.in_focus, self.height)
            self.write_(0, 0, 'test_focus', '*')

    def vmove (self, count = 1):
        self.stream_offset += self.items_per_line * count
        if self.fluent_scroll:
            self.refresh()
        else:
            self.refresh_on_next_tick = True
            self.refresh(height = 2)

    def shift_offset (self, disp):
        if self.reverse_offset_slide:
            self.stream_offset -= disp
        else:
            self.stream_offset += disp
        self.refresh()

    def adjust_items_per_line (self, disp):
        self.items_per_line += disp
        if self.items_per_line < 1: self.items_per_line = 1
        if self.fluent_resize:
            self.refresh()
        else:
            self.refresh_on_next_tick = True
            self.refresh(height = 1)

    def on_input_timeout (self):
        upd = self.stream_cache.reset_updated()
        if self.refresh_on_next_tick or upd:
            self.refresh_on_next_tick = False
            self.refresh()

    def cycle_modes (self):
        if self.show_hex:
            self.show_hex = False
            self.prev_items_per_line = self.items_per_line
            self.items_per_line = max(self.width - 12, 1)
        else:
            self.show_hex = True
            self.items_per_line = self.prev_items_per_line
        self.refresh()

    def jump_to_end (self):
        n = self.items_per_line
        end_offset = self.stream_cache.get_known_end_offset()
        if self.stream_offset <= end_offset \
                and end_offset < self.stream_offset + self.height * n:
            return
        start_ofs_mod = self.stream_offset % n
        bottom_offset = (end_offset - start_ofs_mod + n - 1) // n * n + start_ofs_mod
        self.stream_offset = bottom_offset - n * self.height
        if self.stream_offset <= start_ofs_mod - n:
            self.stream_offset = start_ofs_mod
        self.refresh()

    def jump_to_begin (self):
        n = self.items_per_line
        self.stream_offset = self.stream_offset % n
        if self.stream_offset > 0:
            self.stream_offset -= n;
        self.refresh()

    def on_key (self, key):
        if key in ('j', 'J'): self.vmove(+1)
        elif key in ('k', 'K'): self.vmove(-1)
        elif key in ('g',): self.jump_to_begin()
        elif key in ('G',): self.jump_to_end()
        elif key in ('<', 'h'): self.shift_offset(-1)
        elif key in ('>', 'l'): self.shift_offset(+1)
        elif key in ('_',): self.adjust_items_per_line(-1)
        elif key in ('+',): self.adjust_items_per_line(+1)
        elif key in ('Enter',): self.cycle_modes()
        elif key in ('Ctrl-F', ' '): self.vmove(self.height - 3) # Ctrl-F
        elif key in ('Ctrl-B',): self.vmove(-(self.height - 3)) # Ctrl-B
        elif key in ('Ctrl-D',): self.vmove(self.height // 3) # Ctrl-D
        elif key in ('Ctrl-U',): self.vmove(-(self.height // 3)) # Ctrl-U
        else:
            dmsg("Unknown key: {}", key)

    def on_focus_change (self):
        self.prepare_styles()
        self.refresh()

#* help_window **************************************************************
class help_window (tui.cc_window):
    def __init__ (self):
        dmsg('help_win')
        tui.cc_window.__init__(self,
            init_content = '''
{heading}EBFE - Help

  Welcome to {stress}EBFE{normal}!
            '''.strip())
        self.can_have_focus = True
        self.prepare_styles()

    def on_focus_change (self):
        self.prepare_styles()
        self.refresh()

    def prepare_styles (self):
        if self.in_focus:
            self.set_styles('''
                normal=active_help_normal
                stress=active_help_stress
                key=active_help_key
                heading=active_help_heading
                topic=active_help_topic
            ''')
        else:
            self.set_styles('''
                normal=inactive_help_normal
                stress=inactive_help_stress
                key=inactive_help_key
                heading=inactive_help_heading
                topic=inactive_help_topic
            ''')


DEFAULT_STYLE_MAP = '''
    default attr=normal fg=7 bg=0
    normal_title attr=normal fg=1 bg=7
    passive_title attr=normal fg=0 bg=7
    dash_title attr=bold fg=2 bg=7
    time_title attr=bold fg=4 bg=7

    active_default attr=normal fg=7 bg=4
    active_normal_offset attr=normal fg=7 bg=4
    active_negative_offset attr=normal fg=8 bg=4
    active_offset_item_sep attr=normal fg=6 bg=4
    active_known_item attr=normal fg=7 bg=4
    active_uncached_item attr=normal fg=4 bg=4
    active_missing_item attr=normal fg=8 bg=4
    active_item1_sep attr=normal fg=8 bg=4
    active_item2_sep attr=normal fg=8 bg=4
    active_item4_sep attr=normal fg=8 bg=4
    active_item8_sep attr=normal fg=8 bg=4
    active_item_char_sep attr=normal fg=8 bg=4
    active_normal_char attr=normal fg=6 bg=4
    active_altered_char attr=normal fg=8 bg=4
    active_uncached_char attr=normal fg=12 bg=4
    active_missing_char attr=normal fg=8 bg=4

    inactive_normal_offset attr=normal fg=7 bg=0
    inactive_negative_offset attr=normal fg=8 bg=0
    inactive_offset_item_sep attr=normal fg=6 bg=0
    inactive_known_item attr=normal fg=7 bg=0
    inactive_uncached_item attr=normal fg=4 bg=0
    inactive_missing_item attr=normal fg=8 bg=0
    inactive_item1_sep attr=normal fg=8 bg=0
    inactive_item2_sep attr=normal fg=8 bg=0
    inactive_item4_sep attr=normal fg=8 bg=0
    inactive_item8_sep attr=normal fg=8 bg=0
    inactive_item_char_sep attr=normal fg=8 bg=0
    inactive_normal_char attr=normal fg=6 bg=0
    inactive_altered_char attr=normal fg=8 bg=0
    inactive_uncached_char attr=normal fg=12 bg=0
    inactive_missing_char attr=normal fg=8 bg=0

    default_status_bar attr=normal fg=0 bg=7
    active_console attr=normal fg=0 bg=7
    inactive_console attr=normal fg=7 bg=black
    test_focus attr=normal fg=7 bg=1

    active_help_normal attr=normal fg=7 bg=6
    active_help_stress attr=normal fg=11 bg=6
    active_help_key attr=normal fg=10 bg=6
    active_help_heading attr=normal fg=15 bg=6
    active_help_topic attr=normal fg=5 bg=6

    inactive_help_normal attr=normal fg=7 bg=0
    inactive_help_stress attr=normal fg=11 bg=0
    inactive_help_key attr=normal fg=10 bg=0
    inactive_help_heading attr=normal fg=15 bg=0
    inactive_help_topic attr=normal fg=5 bg=0
'''

#* main *********************************************************************/
class main (tui.application):
    '''
    This is the editor app (and the root window).
    '''

    def __init__ (self, cli):
        tui.application.__init__(self)

        self.server = zlx.io.stream_cache_server()
        for uri in cli.file:
            f = open_file_from_uri(uri)
            sc = zlx.io.stream_cache(f)
            sc = self.server.wrap(sc, cli.load_delay)
            self.stream_windows = []
            sew = stream_edit_window(
                    stream_cache = sc,
                    stream_uri = uri)
            self.stream_windows.append(sew)
        self.active_stream_index = None

        self.panel = help_window()
        self.body = tui.hcontainer(wid = 'body')
        self.body.add(self.panel, weight = 0.3, min_size = 10, max_size = 60)
        self.console_win = console()

        self.root = tui.vcontainer(wid = 'root')
        self.root.add(title_bar('EBFE'), max_size = 1)
        self.root.add(self.body, weight = 10)
        self.root.add(self.console_win, concealed = True)
        self.root.add(status_bar(), max_size = 1)

        self.set_active_stream(0)   
        self.root.focus_to(self.active_stream_win)

    def subwindows (self):
        yield self.root
        return

    def set_active_stream (self, index):
        if self.active_stream_index is not None:
            self.body.del_at_index(0)
            self.active_stream_index = None
        assert index < len(self.stream_windows)
        self.active_stream_index = index
        self.active_stream_win = self.stream_windows[self.active_stream_index]
        self.body.add(self.active_stream_win, index = 0)

    def generate_style_map (self, style_caps):
        return tui.parse_styles(style_caps, DEFAULT_STYLE_MAP)

    def fetch_updates (self):
        return self.root.fetch_updates()

    def on_resize (self, width, height):
        return self.root.resize(width, height)

    def refresh_strip (self, row, col, width):
        return self.root.refresh_strip(row, col, width)

    def quit (self):
        self.server.shutdown()
        raise tui.app_quit(0)

    def on_input_timeout (self):
        self.root.input_timeout()

    def on_key (self, key):
        dmsg('editor: handle key: {!r}', key)
        if key in ('q', 'Q', 'Esc'): self.quit()
        elif key in ('Tab',):
            self.root.cycle_focus(wrap_around = True)
        elif key in (':',):
            self.root.set_item_visibility(self.console_win, toggle = True)
            self.root.focus_to(self.console_win)
        elif key in ('F1',):
            self.body.set_item_visibility(self.panel, toggle = True)
        else:
            self.root.on_key(key)

