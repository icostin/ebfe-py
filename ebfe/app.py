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

    def handle_timeout (self, msg):
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
        tui.window.__init__(self, title,
            styles = '''
            default_status_bar
            '''
        )
        self.title = title
        self.tick = 0

    def refresh_strip (self, row, col, width):
        stext = self.sfmt('{default_status_bar}Test:{}', ' ' * (self.width - 5))
        self.put(0, 0, stext, clip_col = col, clip_width = width)

#* job details **************************************************************
class processing_details (tui.window):
    '''
    Processing Job details
    '''
    def __init__ (self):
        tui.window.__init__(self,
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
            styles = '''
            default_console
            '''
        )
        self.lines_to_display = 8

    def refresh_strip (self, row, col, width):
        stext = self.sfmt('{default_console}{}:{}', row, ' ' * self.width)
        self.put(row, 0, stext, clip_col = col, clip_width = width)
        if self.in_focus and row == 0:
            dmsg("console - ADD FOCUS CHAR TO THE UPDATE LIST")
            self.write_(0, 0, 'test_focus', '*')

#* stream_edit_window *******************************************************
class stream_edit_window (tui.window):
    '''
    This is the window class for stream/file editing.
    '''

    def __init__ (self, stream_cache, stream_uri):
        tui.window.__init__(self, styles='''
            default
            normal_offset negative_offset offset_item_sep
            known_item uncached_item missing_item
            item1_sep item2_sep item4_sep item8_sep
            item_char_sep
            normal_char altered_char uncached_char missing_char
        ''')
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
                        ch = '.'
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

    def tick_tock (self):
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
    
    def handle_keystate (self, msg):
        if msg.ch[1] in ('j', 'J'): self.vmove(+1)
        elif msg.ch[1] in ('k', 'K'): self.vmove(-1)
        elif msg.ch[1] in ('<',): self.shift_offset(-1)
        elif msg.ch[1] in ('>',): self.shift_offset(+1)
        elif msg.ch[1] in ('_',): self.adjust_items_per_line(-1)
        elif msg.ch[1] in ('+',): self.adjust_items_per_line(+1)
        elif msg.ch[1] in ('\n',): self.cycle_modes()
        elif msg.ch[1] in ('\x06', ' '): self.vmove(self.height - 3) # Ctrl-F
        elif msg.ch[1] in ('\x02',): self.vmove(-(self.height - 3)) # Ctrl-B
        elif msg.ch[1] in ('\x04',): self.vmove(self.height // 3) # Ctrl-D
        elif msg.ch[1] in ('\x15',): self.vmove(-(self.height // 3)) # Ctrl-U
        else:
            dmsg("Unknown key: {}", msg.ch)

#* editor *******************************************************************
class editor (tui.application):
    '''
    This is the editor app (and the root window).
    '''

    def __init__ (self, cli):
        tui.application.__init__(self)

        self.server = zlx.io.stream_cache_server()

        self.tick = 0
        self.title_bar = title_bar('ebfe - EBFE Binary File Editor')

        self.job_details = processing_details()
        #self.job_details.can_have_focus = True
        self.job_details.show = False
        
        self.console = console()
        self.console.can_have_focus = True
        self.console.show = False

        self.mode = 'normal' # like vim normal mode

        self.stream_windows = []
        if not cli.file:
            cli.file.append('mem://0')

        for uri in cli.file:
            f = open_file_from_uri(uri)
            sc = zlx.io.stream_cache(f)
            #sc.load(0, sc.blocks[len(sc.blocks) - 1].offset // 2)
            sc = self.server.wrap(sc, cli.load_delay)
            sew = stream_edit_window(
                    stream_cache = sc,
                    stream_uri = uri)
            self.stream_windows.append(sew)

        self.active_stream_index = 0
        self.active_stream_win = self.stream_windows[self.active_stream_index]
        self.active_stream_win.can_have_focus = True

        # Build the list of windows which can receive focus
        self.win_focus_list = []
        #self.win_focus_list.append(self.job_details)   # made focusable for testing purposes
        self.win_focus_list.append(self.active_stream_win)
        self.win_focus_list.append(self.console)
        self.focus_index = 0                            # it won't change focus if window is not visible anyways
        self.old_focus_index = self.focus_index         # init the old as well
        self.focus_to(self.active_stream_win)
        
        self.status_bar = status_bar('EBFE Binary File Editor')

    def focus_next (self):
        index = self.focus_index
        s = len(self.win_focus_list)
        for i in range(s):
            index += 1
            if index >= s:
                index = 0
            # break if we are back where we started
            if index == self.focus_index:
                break
            if self.win_focus_list[index].show:
                self.process_focus(index)
                self.refresh()
                break

    def focus_to (self, w):
        if w.can_have_focus and w.show:
            for index in range(len(self.win_focus_list)):
                if w is self.win_focus_list[index]:
                    self.process_focus(index)

    def focus_back (self):
        index = self.old_focus_index
        w = self.win_focus_list[index]
        if not w.can_have_focus or not w.show:
            self.focus_to(self.active_stream_win)
        else:
            self.process_focus(index)
        #self.focus_to(self.active_stream_win)

    def process_focus (self, index):
        self.win_focus_list[self.focus_index].focus(False)
        self.old_focus_index = self.focus_index
        self.focus_index = index
        self.win_focus_list[index].focus()
        #out = ''
        #for w in self.win_focus_list:
        #    if w.in_focus:
        #        out += 'YES '
        #    else:
        #        out += 'NO '
        #dmsg("WINDOW STATUS: {}", out)
        #self.refresh()

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
            negative_offset attr=normal fg=8 bg=0
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
            default_status_bar attr=normal fg=7 bg=4
            default_console attr=normal fg=0 bg=7
            test_focus attr=normal fg=7 bg=1
            ''')
        return sm

    def resize (self, width, height):
        h = 0
        self.width = width
        self.height = height

        if width > 0 and height > 0: 
            self.title_bar.resize(width, 1)
            self.title_bar.render_starting_line = 0
            h += 1
            
            if self.job_details.show and height > self.job_details.lines_to_display + h:
                self.job_details.resize(width, self.job_details.lines_to_display)
                self.job_details.render_starting_line = 1
                h += self.job_details.lines_to_display
            else:
                self.job_details.resize(width, 0)
                self.job_details.render_starting_line = -1

            if height > h:
                self.status_bar.resize(width, 1)
                self.status_bar.render_starting_line = height - 1
                h += 1
            
            if self.console.show and height > h:
                self.console.resize(width, self.console.lines_to_display)
                self.console.render_starting_line = height - (1 + self.console.lines_to_display)
                h += self.console.lines_to_display
            else:
                self.console.resize(width, 0)
                self.console.render_starting_line = -1

            if self.active_stream_win and width > 0 and height > h:
                self.active_stream_win.resize(width, height - h)
                if self.job_details.show:
                    self.active_stream_win.render_starting_line = self.job_details.lines_to_display + 1
                else:
                    self.active_stream_win.render_starting_line = 1     # just the title bar

        self.refresh()

    def refresh_strip (self, row, col, width):
        # title bar
        if  row == 0:
            self.title_bar.refresh_strip(0, col, width)
            self.integrate_updates(0, 0, self.title_bar.fetch_updates())
        # processing details
        elif (self.job_details.show 
                and row >= self.job_details.render_starting_line 
                and row < self.job_details.render_starting_line + self.job_details.height
            ):
            self.job_details.refresh_strip(row - self.job_details.render_starting_line, col, width)
            self.integrate_updates(self.job_details.render_starting_line, 0, self.job_details.fetch_updates())
        # hex edit with processing details active
        elif (row >= self.active_stream_win.render_starting_line 
                and row < self.active_stream_win.render_starting_line + self.active_stream_win.height 
                and self.active_stream_win
                ):
            self.active_stream_win.refresh_strip(row - self.active_stream_win.render_starting_line, col, width)
            self.integrate_updates(self.active_stream_win.render_starting_line, 0, self.active_stream_win.fetch_updates())
        # console
        elif (self.console.show 
                and row >= self.console.render_starting_line 
                and row < self.console.render_starting_line + self.console.height
            ):
            self.console.refresh_strip(row - self.console.render_starting_line, col, width)
            self.integrate_updates(self.console.render_starting_line, 0, self.console.fetch_updates())
        # status bar
        elif (row >= self.status_bar.render_starting_line 
                and row < self.status_bar.render_starting_line + self.status_bar.height
                ):
            self.status_bar.refresh_strip(row - self.status_bar.render_starting_line, col, width)
            self.integrate_updates(self.status_bar.render_starting_line, 0, self.status_bar.fetch_updates())
        # anything else ?!? Fill in with the -----+------
        else:
            tui.application.refresh_strip(self, row, col, width)

    def handle_timeout (self, msg):
        self.title_bar.handle_timeout(msg)
        #self.status_bar.handle_timeout(msg)
        self.act('tick_tock')
        self.integrate_updates(0, 0, self.title_bar.fetch_updates())
        if self.job_details.show:
            self.integrate_updates(1, 0, self.job_details.fetch_updates())
        self.integrate_updates(self.height-1, 0, self.status_bar.fetch_updates())

    def act (self, func, *l, **kw):
        if self.active_stream_win:
            getattr(self.active_stream_win, func)(*l, **kw)
            self.integrate_updates(1 + self.job_details.height, 0, self.active_stream_win.fetch_updates())

    def quit (self):
        self.server.shutdown()
        raise tui.app_quit(0)

    def handle_keystate (self, msg):
        if msg.ch[1] in ('q', 'Q', 'ESC'): self.quit()
        elif msg.ch[1] in ('\t',): self.focus_next() # Ctrl-TAB
        elif msg.ch[1] in ('w',):
            if self.job_details.show:
                self.job_details.show = False
                if self.job_details.in_focus:
                    self.focus_back()
            else:
                self.job_details.show = True
                self.focus_to(self.job_details)
            self.resize(self.width, self.height)
            dmsg("Height job: {}, height hex: {}", self.job_details.height, self.active_stream_win.height)
        elif msg.ch[1] in (':',):
            if self.console.show:
                self.console.show = False
                if self.console.in_focus:
                    self.focus_back()
            else:
                self.console.show = True
                self.focus_to(self.console)
            self.resize(self.width, self.height)

        # All these messages need to be routed to the window in focus
        else:
            for w in self.win_focus_list:
                if w.in_focus:
                    if hasattr(w, 'handle_keystate'):
                        getattr(w, 'handle_keystate')(msg)
                        self.integrate_updates(w.render_starting_line, 0, w.fetch_updates())
                        #self.refresh()

