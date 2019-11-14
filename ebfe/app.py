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

PRINTABLE_ASCII_CHARMAP = '._______________________________' + \
        ''.join(chr(x) for x in range(32, 127)) + \
        ''.join('_' for x in range(127, 255)) + '#'
assert len(PRINTABLE_ASCII_CHARMAP) == 256

CP437_CHARMAP = ''.join([
'\u0020', '\u263A', '\u263B', '\u2665', '\u2666', '\u2663', '\u2660', '\u2022',
'\u25D8', '\u25CB', '\u25D9', '\u2642', '\u2640', '\u266A', '\u266B', '\u263C',
'\u25BA', '\u25C4', '\u2195', '\u203C', '\u00B6', '\u00A7', '\u25AC', '\u21A8',
'\u2191', '\u2193', '\u2192', '\u2190', '\u221F', '\u2194', '\u25B2', '\u25BC',
'\u0020', '\u0021', '\u0022', '\u0023', '\u0024', '\u0025', '\u0026', '\u0027',
'\u0028', '\u0029', '\u002A', '\u002B', '\u002C', '\u002D', '\u002E', '\u002F',
'\u0030', '\u0031', '\u0032', '\u0033', '\u0034', '\u0035', '\u0036', '\u0037',
'\u0038', '\u0039', '\u003A', '\u003B', '\u003C', '\u003D', '\u003E', '\u003F',
'\u0040', '\u0041', '\u0042', '\u0043', '\u0044', '\u0045', '\u0046', '\u0047',
'\u0048', '\u0049', '\u004A', '\u004B', '\u004C', '\u004D', '\u004E', '\u004F',
'\u0050', '\u0051', '\u0052', '\u0053', '\u0054', '\u0055', '\u0056', '\u0057',
'\u0058', '\u0059', '\u005A', '\u005B', '\u005C', '\u005D', '\u005E', '\u005F',
'\u0060', '\u0061', '\u0062', '\u0063', '\u0064', '\u0065', '\u0066', '\u0067',
'\u0068', '\u0069', '\u006A', '\u006B', '\u006C', '\u006D', '\u006E', '\u006F',
'\u0070', '\u0071', '\u0072', '\u0073', '\u0074', '\u0075', '\u0076', '\u0077',
'\u0078', '\u0079', '\u007A', '\u007B', '\u007C', '\u007D', '\u007E', '\u2302',
'\u00C7', '\u00FC', '\u00E9', '\u00E2', '\u00E4', '\u00E0', '\u00E5', '\u00E7',
'\u00EA', '\u00EB', '\u00E8', '\u00EF', '\u00EE', '\u00EC', '\u00C4', '\u00C5',
'\u00C9', '\u00E6', '\u00C6', '\u00F4', '\u00F6', '\u00F2', '\u00FB', '\u00F9',
'\u00FF', '\u00D6', '\u00DC', '\u00A2', '\u00A3', '\u00A5', '\u20A7', '\u0192',
'\u00E1', '\u00ED', '\u00F3', '\u00FA', '\u00F1', '\u00D1', '\u00AA', '\u00BA',
'\u00BF', '\u2310', '\u00AC', '\u00BD', '\u00BC', '\u00A1', '\u00AB', '\u00BB',
'\u2591', '\u2592', '\u2593', '\u2502', '\u2524', '\u2561', '\u2562', '\u2556',
'\u2555', '\u2563', '\u2551', '\u2557', '\u255D', '\u255C', '\u255B', '\u2510',
'\u2514', '\u2534', '\u252C', '\u251C', '\u2500', '\u253C', '\u255E', '\u255F',
'\u255A', '\u2554', '\u2569', '\u2566', '\u2560', '\u2550', '\u256C', '\u2567',
'\u2568', '\u2564', '\u2565', '\u2559', '\u2558', '\u2552', '\u2553', '\u256B',
'\u256A', '\u2518', '\u250C', '\u2588', '\u2584', '\u258C', '\u2590', '\u2580',
'\u03B1', '\u00DF', '\u0393', '\u03C0', '\u03A3', '\u03C3', '\u00B5', '\u03C4',
'\u03A6', '\u0398', '\u03A9', '\u03B4', '\u221E', '\u03C6', '\u03B5', '\u2229',
'\u2261', '\u00B1', '\u2265', '\u2264', '\u2320', '\u2321', '\u00F7', '\u2248',
'\u00B0', '\u2219', '\u00B7', '\u221A', '\u207F', '\u00B2', '\u25A0', '\u00A0'
])
assert len(CP437_CHARMAP) == 256

TWEAKED_CP437_CHARMAP = '.' + CP437_CHARMAP[1:-1] + '#'
assert len(TWEAKED_CP437_CHARMAP) == 256

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
            ''')
        self.lines_to_display = 1

    def refresh_strip (self, row, col, width):
        stext = self.sfmt('{default_status_bar}Working...{}', ' ' * (self.width - 10))
        self.put(row, 0, stext, clip_col = col, clip_width = width)

#* console ******************************************************************
class console (tui.container):
    '''
    Console for commands
    '''

    ACTIVE_STYLES = '''
            normal=active_console
    '''

    INACTIVE_STYLES = '''
            normal=inactive_console
    '''

    def __init__ (self, wid = None):
        tui.container.__init__(self,
                wid = wid,
                direction = tui.container.VERTICAL)
        self.msg_win = tui.cc_window(
                init_content = 'This is the console area.',
                can_have_focus = False,
                styles = self.INACTIVE_STYLES,
                active_styles = self.ACTIVE_STYLES)
        self.input_win = tui.input_line(
                styles = self.INACTIVE_STYLES,
                active_styles = self.ACTIVE_STYLES,
                accept_text_func = self._accept_input)
        self.add(self.msg_win)
        self.add(self.input_win, max_size = 1)

    def _accept_input (self, text):
        self.msg_win.set_content(len(self.msg_win.content), text)
        self.input_win.erase_text()

    def on_focus_enter (self):
        self.msg_win.select_theme('active')
        #self.input_win.select_theme('active')
        tui.container.on_focus_enter(self)
        self.integrate_updates(*self._get_item_row_col(self.items_[0]), self.msg_win.fetch_updates())
        #self.refresh()

    def on_focus_leave (self):
        self.msg_win.select_theme('inactive')
        #self.input_win.select_theme('inactive')
        tui.container.on_focus_leave(self)
        self.integrate_updates(*self._get_item_row_col(self.items_[0]), self.msg_win.fetch_updates())
        #self.refresh()

#* stream_edit_window *******************************************************
class stream_edit_window (tui.window):
    '''
    This is the window class for stream/file editing.
    '''

    ACTIVE_STYLES = '''
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
    '''

    INACTIVE_STYLES = '''
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
    '''

# stream_edit_window.__init__
    def __init__ (self, stream_cache, stream_uri):
        tui.window.__init__(self,
                styles = self.INACTIVE_STYLES,
                active_styles = self.ACTIVE_STYLES,
                can_have_focus = True)
        cfg = settings_manager(os.path.expanduser('~/.ebfe.ini'))
        self.stream_uri = stream_uri
        self.stream_cache = stream_cache
        self.stream_offset = 0
        self.cursor_offset = 0
        self.cursor_strip = 0
        #self.offset_format = '{:+08X}: '
        self.items_per_line = cfg.iget('window: hex edit', 'items_per_line', 16)
        self.prev_items_per_line = self.items_per_line
        self.column_size = cfg.iget('window: hex edit', 'column_size', 4)
        self.fluent_scroll = cfg.bget('window: hex edit', 'fluent_scroll', True)
        self.fluent_resize = cfg.bget('window: hex edit', 'fluent_resize', True)
        self.reverse_offset_slide = cfg.bget('window: hex edit', 'reverse_offset_slide', True)
        self.refresh_on_next_tick = False
        self.show_hex = True
        self.character_display = cfg.get('window: hex edit', 'charmap', 'printable_ascii')
        self.charmap = globals()[self.character_display.upper() + '_CHARMAP']
        self.temp_demo_update_strip = False

# stream_edit_window.refresh_strip
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
                    else:
                        cstrip_style = '{altered_char}'
                    if cstrip_style != last_cstrip_style:
                        cstrip += self.sfmt(cstrip_style)
                        last_cstrip_style = cstrip_style
                    ch = self.charmap[b]
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

        if self.temp_demo_update_strip and row == 3:
            self.update_style(row, 3, 6, 'normal_title')
            self.update_style(row, 11, 21, lambda s: 'in' + s.style_name if s.style_name.startswith('active') else s.style_name)

        if row == self.cursor_strip:
            strip_bin_offset =self.cursor_offset - (self.stream_offset + (self.items_per_line * row))
            extra_offset_hex = strip_bin_offset // self.column_size
            extra_offset_hex += 10      # skip the offset

            extra_offset_ascii = self.items_per_line // self.column_size
            if self.items_per_line % self.column_size > 0:
                extra_offset_ascii += 1
            extra_offset_ascii += 10      # skip the offset
            extra_offset_ascii += self.items_per_line * 3

            self.update_style(row, strip_bin_offset * 3 + extra_offset_hex, 2, 'normal_title')
            self.update_style(row, strip_bin_offset + extra_offset_ascii, 1, 'normal_title')


# stream_edit_window.move_cursor_to_offset
    def move_cursor_to_offset (self, ofs, percentage=50):
        stream_shift = self.stream_offset % self.items_per_line
        shift = ofs % self.items_per_line
        half = ((self.height * percentage) // 100) * self.items_per_line
        self.stream_offset = ofs - half - shift + stream_shift
        self.cursor_offset = ofs
        self.cursor_strip = (ofs - self.stream_offset) // self.items_per_line
        self.refresh()

# stream_edit_window.move_cursor
    def move_cursor (self, x, y):
        old_strip = self.cursor_strip
        new_offset = self.cursor_offset + x + (y * self.items_per_line)
        # If new offset for cursor is negative then we don't update anything
        if new_offset < 0:
            return
        self.cursor_offset = new_offset

        strip = (new_offset - self.stream_offset) // self.items_per_line
        
        # if the strip is negative then we just set it to 0 and scroll up the window
        if strip < 0:
            self.cursor_strip = 0
            self.stream_offset -= -strip * self.items_per_line
            self.refresh()
        elif strip > self.height-1:
            self.cursor_strip = self.height-1
            self.stream_offset += (strip - (self.height - 1)) * self.items_per_line
            self.refresh()
        else:
            # if cursor move doesn't require a window scroll then refresh a maximum of two lines
            self.cursor_strip = strip

            if old_strip == strip:
                self.refresh(start_row = strip, height = 1)
            else:
                self.refresh(start_row = old_strip, height = 1)
                self.refresh(start_row = strip, height = 1)

# stream_edit_window.vmove
    def vmove (self, count = 1):
        self.stream_offset += self.items_per_line * count
        if self.fluent_scroll:
            self.move_cursor(0, 0)
            self.refresh()
        else:
            self.move_cursor(0, 0)
            self.refresh_on_next_tick = True
            self.refresh(height = 2)

# stream_edit_window.shift_offset
    def shift_offset (self, disp):
        if self.reverse_offset_slide:
            self.stream_offset -= disp
        else:
            self.stream_offset += disp
        self.move_cursor(0, 0)
        self.refresh()

# stream_edit_window.adjust_items_per_line
    def adjust_items_per_line (self, disp):
        self.items_per_line += disp
        if self.items_per_line < 1: self.items_per_line = 1
        if self.fluent_resize:
            self.move_cursor(0, 0)
            self.refresh()
        else:
            self.move_cursor(0, 0)
            self.refresh_on_next_tick = True
            self.refresh(height = 1)

# stream_edit_window.on_input_timeout
    def on_input_timeout (self):
        upd = self.stream_cache.reset_updated()
        if self.refresh_on_next_tick or upd:
            self.move_cursor(0, 0)
            self.refresh_on_next_tick = False
            self.refresh()

# stream_edit_window.cycle_modes
    def cycle_modes (self):
        if self.show_hex:
            self.show_hex = False
            self.prev_items_per_line = self.items_per_line
            self.items_per_line = max(self.width - 12, 1)
        else:
            self.show_hex = True
            self.items_per_line = self.prev_items_per_line
        self.move_cursor(0, 0)
        self.refresh()

# stream_edit_window.jump_to_end
    def jump_to_end (self):
        #n = self.items_per_line
        #end_offset = self.stream_cache.get_known_end_offset()
        #if self.stream_offset <= end_offset \
        #        and end_offset < self.stream_offset + self.height * n:
        #    return
        #start_ofs_mod = self.stream_offset % n
        #bottom_offset = (end_offset - start_ofs_mod + n - 1) // n * n + start_ofs_mod
        #self.stream_offset = bottom_offset - n * self.height
        #if self.stream_offset <= start_ofs_mod - n:
        #    self.stream_offset = start_ofs_mod
        self.move_cursor_to_offset(self.stream_cache.get_known_end_offset() - 1, 90)
        #self.cursor_offset = self.stream_cache.get_known_end_offset() - 1
        #self.move_cursor(0, 0)
        self.refresh()

# stream_edit_window.jump_to_begin
    def jump_to_begin (self):
        #n = self.items_per_line
        #self.stream_offset = self.stream_offset % n
        #if self.stream_offset > 0:
        #    self.stream_offset -= n;
        self.cursor_offset = 0
        self.move_cursor(0, 0)
        self.refresh()

# stream_edit_window.on_key
    def on_key (self, key):
        if key in ('j', 'J'): self.vmove(+1)
        elif key in ('k', 'K'): self.vmove(-1)
        elif key in ('g',): self.jump_to_begin()
        elif key in ('G',): self.jump_to_end()
        elif key in ('<', 'h'): self.shift_offset(-1)
        elif key in ('>', 'l'): self.shift_offset(+1)
        elif key in ('_',): self.adjust_items_per_line(-1)
        elif key in ('+',): self.adjust_items_per_line(+1)
        elif key in ('T',):
            self.temp_demo_update_strip = not self.temp_demo_update_strip
            self.refresh(start_row = 3, height = 1)
        elif key in ('H',):
            #self.cursor_offset = 0x500
            #self.move_cursor(0, 0)
            self.move_cursor_to_offset(0x500, percentage=80)
        elif key in ('Enter',): self.cycle_modes()
        elif key in ('Ctrl-F', ' '): self.vmove(self.height - 3) # Ctrl-F
        elif key in ('Ctrl-B',): self.vmove(-(self.height - 3)) # Ctrl-B
        elif key in ('Ctrl-D',): self.vmove(self.height // 3) # Ctrl-D
        elif key in ('Ctrl-U',): self.vmove(-(self.height // 3)) # Ctrl-U
        elif key in ('Left'): self.move_cursor(-1, 0)
        elif key in ('Up'): self.move_cursor(0, -1)
        elif key in ('Right'): self.move_cursor(1, 0)
        elif key in ('Down'): self.move_cursor(0, 1)
        else:
            dmsg("Unknown key: {}", key)
            return False
        return True

# stream_edit_window.on_focus_change()
    def on_focus_change (self):
        tui.window.on_focus_change(self)
        self.set_cursor(tui.CM_INVISIBLE)

#* help_window **************************************************************
class help_window (tui.simple_doc_window):

    ACTIVE_STYLES = '''
        normal=active_help_normal
        stress=active_help_stress
        key=active_help_key
        heading=active_help_heading
        topic=active_help_topic
    '''

    INACTIVE_STYLES = '''
        normal=inactive_help_normal
        stress=inactive_help_stress
        key=inactive_help_key
        heading=inactive_help_heading
        topic=inactive_help_topic
    '''

    INIT_CONTENT = '''
{br}
{heading}EBFE - Help{normal}

{par}{justify}
Welcome to {stress}EBFE{normal}!




While we absolutely love the Unix phylosophy, minimalism in design
sometimes manifests itself in the form of books to describe the subject
(see 'How to exit Vim'). While you totally deserve a steep learning curve
for trying some new piece software, allow us to insult your tarot abilities
with some default key-mappings to keep you going before you hit the shelves.


{par}{wrap_indent}8{stress}Global keys:{br}
{key}Esc{normal}{tab}8{cpar}    close/cancel/exit from current activity{br}
{key}Tab{normal}{tab}8{cpar}    cycle focus between windows{br}
{key}:{normal}{tab}8{cpar}      open (or switch to) command window{br}
{key}F1{normal}{tab}8{cpar}     toggle this help window{br}
{key}Alt-x{normal}{tab}8{cpar}  exit{br}


{par}{stress}Hex editor window keys:{br}
{key}Up{normal}, {key}k{normal}{tab}12{cpar}    move up{br}
{key}Down{normal}, {key}j{normal}{tab}12{cpar}  move down{br}
{hr}
    '''.strip()

    def __init__ (self):
        dmsg('help_win')
        tui.simple_doc_window.__init__(self,
            doc_fmt = self.INIT_CONTENT,
            styles = self.INACTIVE_STYLES,
            active_styles = self.ACTIVE_STYLES,
            can_have_focus = True)


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
    active_console attr=normal fg=11 bg=6
    inactive_console attr=normal fg=7 bg=black
    test_focus attr=normal fg=7 bg=1

    active_help_normal attr=normal fg=15 bg=6
    active_help_stress attr=normal fg=11 bg=6
    active_help_key attr=normal fg=10 bg=6
    active_help_heading attr=normal fg=5 bg=6
    active_help_topic attr=normal fg=5 bg=6

    inactive_help_normal attr=normal fg=7 bg=0
    inactive_help_stress attr=normal fg=15 bg=0
    inactive_help_key attr=normal fg=10 bg=0
    inactive_help_heading attr=normal fg=11 bg=0
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
        self.stream_windows = []
        file_uris = cli.file or ('mem://0',)
        for uri in file_uris:
            dmsg('uri={!r}', uri)
            f = open_file_from_uri(uri)
            sc = zlx.io.stream_cache(f)
            sc = self.server.wrap(sc, cli.load_delay)
            sew = stream_edit_window(
                    stream_cache = sc,
                    stream_uri = uri)
            self.stream_windows.append(sew)
        dmsg('stream windows: {!r}', self.stream_windows)
        self.active_stream_index = None

        self.panel = help_window()
        self.body = tui.hcontainer(wid = 'body')
        self.body.add(self.panel, weight = 0.3, min_size = 10, max_size = 60)
        self.console_win = console()
        self.console_win.input_win.cancel_text_func = self._cancel_console_input

        self.root = tui.vcontainer(wid = 'root')
        self.root.add(title_bar('EBFE'), max_size = 1)
        self.root.add(self.body, weight = 10)
        self.root.add(self.console_win, concealed = True)
        self.root.add(status_bar(), max_size = 1)

        #self.set_active_stream(0)
        for i in range(len(self.stream_windows)):
            sw = self.stream_windows[i]
            dmsg('adding in container window for {!r}', file_uris[i])
            self.body.add(sw, index = i)
        self.active_stream_win = self.stream_windows[0]

        self.root.focus_to(self.active_stream_win)

    def _cancel_console_input (self):
        if self.console_win.input_win.text:
            self.console_win.input_win.erase_text()
        else:
            self.root.set_item_visibility(self.console_win, False)

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

        # handle global shortcuts first
        if key in ('Tab', ):
            self.root.cycle_focus(wrap_around = True)
            return True
        if key in ('Alt-x', ):
            self.quit()

        if key in ('F1',):
            self.body.set_item_visibility(self.panel, toggle = True)
            return True

        # pass to focused window
        if self.root.on_key(key):
            return True

        # handle keys not used by the focused window
        if key in ('q', 'Q', 'Esc'): self.quit()
        elif key in (':',):
            self.root.set_item_visibility(self.console_win, True)
            self.root.focus_to(self.console_win)

