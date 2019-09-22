import functools
from collections import namedtuple

import zlx.record
from zlx.io import dmsg

class error (RuntimeError):
    pass

class app_quit (error):
    def __init__ (self, ret_code = 0):
        error.__init__(self, 'quit tui app')
        self.ret_code = ret_code
    pass

# attributes to be used in style (:-D all puns intended)
A_NORMAL = 0
A_BOLD = 1
A_ITALIC = 2
A_ALT_CHARSET = 4

STYLE_PARSE_MAP = dict(
        normal = A_NORMAL,
        bold = A_BOLD,
        italic = A_ITALIC,
        altchar = A_ALT_CHARSET,
        black = 0,
        red = 1,
        green = 2,
        yellow = 3,
        blue = 4,
        magenta = 5,
        cyan = 6,
        grey = 7,
    )

screen_size = namedtuple('screen_size', 'width height'.split())

style_caps = namedtuple('style_caps', 'attr fg_count bg_count fg_default bg_default'.split())


#* message ******************************************************************
class message (object):
    '''
    Represents an event generated by a tui driver.
    A driver may derive this or use it as it is.
    '''
    def __init__ (self, *l, **kw):
        object.__init__(self)
        if l:
            for i in range(len(l)):
                setattr(self, self.__slots__[i], l[i])
        for k, v in kw.items():
            setattr(self, k, v)

#* resize_message ***********************************************************
class resize_message (message):
    __slots__ = 'width height'.split()
    name = 'resize'

#* driver *******************************************************************
class driver (object):
    '''
    Input and display driver.
    Derive this to provide an interface I/O.
    '''
    def __init__ (self):
        object.__init__(self)

    def get_screen_size (self):
        raise RuntimeError('must be implemented in derived class')

    def get_style_caps (self):
        '''
        Overload this to return the capabilites for styles.
        The function should return a style_caps object
        '''
        return style_caps(A_NORMAL, 1, 1, 0, 0)

    def register_styles (self, style_map):
        '''
        Processes the given map and for each style calls register_style()
        storing the returned object.
        No need to overload this.

        '''
        self.style_map = {}
        for k, v in style_map.items():
            self.style_map[k] = self.build_style(v)

    def build_style (self, style):
        '''
        Process the tui attributes and colors and generate whatever is needed
        by the driver to display text with those specs.
        Overload this!
        '''
        return style

    def get_message (self):
        '''
        Overload this or else...
        '''
        return message('quit')

    
    def render (self, updates):
        '''
        Goes through all update strips and renders them.
        No need to overload this.
        '''
        for row, strips in updates.items():
            for s in strips:
                self.render_text(s.text, s.style_name, s.col, row)

    def render_text (self, text, style_name, column, row):
        '''
        Overload this to output.
        '''
        pass



#* style ********************************************************************
class style (zlx.record.Record):
    '''
    Describes the style for a portion of text.
    Instantiate with: style(fg, bg, attr)
    '''
    __slots__ = 'attr fg bg'.split()

class strip (zlx.record.Record):
    '''
    A strip is a portion of a one line of text with its style.
    '''

#* make_style ***************************************************************
def make_style (caps, 
        fg = None, bg = None, attr = A_NORMAL, 
        fg256 = None, bg256 = None, attr256 = None):
    '''
    creates a style object that fits within the given caps
    '''
    if caps.fg_count == 256 and fg256 is not None: fg = fg256
    if caps.bg_count == 256 and bg256 is not None: bg = bg256
    if caps.bg_count == 256 and attr256 is not None: attr = attr256
    if fg is None or fg >= caps.fg_count: fg = caps.fg_default
    if bg is None or bg >= caps.bg_count: bg = caps.bg_default
    attr &= caps.attr
    return style(attr, fg, bg)

#* parse_styles *************************************************************
def parse_styles (caps, src):
    m = {}
    for line in src.splitlines():
        if '#' in line: line = line[0:line.index('#')]
        line = line.strip()
        if line == '': continue
        name, *attrs = line.split()
        d = {}
        for a in attrs:
            k, v = a.split('=', 1)
            vparts = (STYLE_PARSE_MAP[x] if x in STYLE_PARSE_MAP else int(x) for x in v.split('|'))
            d[k] = functools.reduce(lambda a, b: a | b, vparts)
        m[name] = make_style(caps, **d)
    return m

#* strip ********************************************************************
strip = zlx.record.make('tui.strip', 'text style_name col')

#* compute_text_width *******************************************************
def compute_text_width (text):
    return len(text)

#* compute_index_of_column **************************************************
def compute_index_of_column (text, column):
    '''
    Computes the index in the text corresponding to given column, assuming
    index 0 corresponds to column 0.
    This should take into account the width of unicode chars displayed.
    Returns None if the text does not reach that column.
    '''
    return column

STYLE_BEGIN = '\a'
STYLE_END = '\b'

#* styled_text_chunks *******************************************************
def styled_text_chunks (styled_text, initial_style = 'default'):
    for x in ''.join((initial_style, STYLE_END, styled_text)).split(STYLE_BEGIN):
        style, text = x.split(STYLE_END, 1)
        if not text: continue
        yield (style, text)

#* strip_styles_from_styled_text ********************************************
def strip_styles_from_styled_text (styled_text):
    return ''.join((x.split(STYLE_END, 1)[1] for x in (STYLE_END + text).split(STYLE_BEGIN)))

#* get_char_width ***********************************************************
def get_char_width (ch):
    return 1

#* compute_styled_text_index_of_column **************************************
def compute_styled_text_index_of_column (styled_text, column):
    '''
    Computes the index in the text corresponding to given column, assuming
    index 0 corresponds to column 0.
    This should take into account the width of unicode chars displayed.
    Returns a pair (index, column). column may be smaller than column if
    the char at index is double-width and would jump over requested column.
    If the string is not as wide to reach the column the function returns
    (None, text_width)
    '''
    c = 0
    text_mode = True
    for i in range(len(styled_text)):
        if text_mode:
            ch = styled_text[i]
            if ch == STYLE_BEGIN:
                text_mode = False
                continue
            w = get_char_width(ch)
            if c + w > column: return i, c
            c += w
        else:
            if styled_text[i] == STYLE_END:
                text_mode = True
    return None, c

#* compute_styled_text_width ************************************************
def compute_styled_text_width (styled_text):
    return compute_styled_text_index_of_column(styled_text, 9999)[1]

#* window *******************************************************************
class window (object):
    '''
    A window has width and height and a list of updates.
    The updates are organized as a list for each row where elements are
    strips.
    Recommended overloads:
    - various message handlers: handle_xxx() (handle_timeout, handle_char)
    - refresh_strip() - to generate output for a row portion when asked
    - resize() - if the window has children or custom fields need adjusting
    '''

    def __init__ (self, width = 0, height = 0, styles = 'default'):
        object.__init__(self)
        self.width = width
        self.height = height
        self.style_names = styles.split()
        self.default_style_name = self.style_names[0]
        self.style_markers = { s: '\a{}\b'.format(s) for s in self.style_names }
        self.wipe_updates()

    def wipe_updates (self):
        '''
        Empties the strips from the updates field.
        No need to overload this.
        '''
        self.updates = {}

    def write_ (self, row, col, style_name, text):
        '''
        Adds the given text in the right place in the updates field.
        No need to overload this.
        '''
        if row not in self.updates:
            self.updates[row] = []
        row_strips = self.updates[row]
        row_strips.append(strip(text, style_name, col))
        pass

    def write (self, row, col, style_name, text, clip_col = 0, clip_width = None):
        '''
        Adds the given text taking into account the given clipping coords.
        No need to overload this.
        '''
        if col < clip_col:
            i = compute_index_of_column(text, clip_col - col)
            if i is None: return
            col = clip_col
            text = text[i:]
        clip_end_col = clip_col + clip_width if clip_width is not None else self.width
        if clip_end_col > self.width: clip_end_col = self.width
        i = compute_index_of_column(text, clip_end_col - col)
        if i is not None: text = text[:i]
        self.write_(row, col, style_name, text)

    def sfmt (self, fmt, *l, **kw):
        '''
        Format text with styles.
        '''
        return fmt.format(*l, **kw, **self.style_markers)

    def put (self, row, col, styled_text, clip_col = 0, clip_width = None):
        for style, text in styled_text_chunks(styled_text, self.default_style_name):
            self.write(row, col, style, text, clip_col, clip_width)
            col += compute_text_width(text)
        pass

    def integrate_updates (self, row_delta, col_delta, updates):
        for row in updates:
            for s in updates[row]:
                self.write(row + row_delta, s.col + col_delta, s.style_name, s.text)
        return

    def refresh_strip (self, row, col, width):
        '''
        Refreshes the content a strip of the window.
        Overload this to implement displaying content in your window.
        Normally you want to call write() with text to cover all length
        of the given strip.
        This should ideally not do blocking operations as for good UX it must
        be fast.
        '''
        txt = ('.' if row else '-') * (self.width // 2) + '+' 
        txt += txt[0] * (self.width - self.width // 2)
        self.write(row, col, 'default', txt[col:col + width])

    def refresh (self,
            start_row = 0,
            start_col = 0,
            height = None,
            width = None):
        '''
        Calls refresh_strip() for each row in given range.
        if height or width are left None they will cover the window to its
        border.
        Calling this method without explicit args causes entire window to be
        redrawn.
        No need to overload this.
        '''
        if start_row >= self.height or start_col >= self.width: return

        if height is None: height = self.height
        if width is None: width = self.width

        end_row = min(self.height, start_row + height)
        width = min(self.width - start_col, width)

        for r in range(start_row, end_row):
            self.refresh_strip(r, start_col, width)

    def resize (self, width, height):
        '''
        Updates window size and refreshes whole content.
        Overload this if the window has children or addition state needs to
        be adjusted
        '''
        self.width = width
        self.height = height
        self.refresh()

    def handle (self, msg):
        '''
        Message handler.
        No need to overload this, instead create/overload methods named
            handle_<message_name>
        '''
        handler_name = 'handle_' + msg.name
        if hasattr(self, handler_name):
            getattr(self, handler_name)(msg)

    def handle_resize (self, msg):
        '''
        Default handler for window resize!
        '''
        self.resize(msg.width, msg.height)

    def fetch_updates (self):
        '''
        Extracts the updates from this window.
        No need to overload this
        '''
        u = self.updates
        self.wipe_updates()
        return u

class application (window):
    '''
    Represents a Text UI application.
    This class represents the root window of the app plus a way of 
    describing the styles that are used when displaying text
    Derive to taste.
    Recommended overloads:
    - generate_style_map() - to generate style according to driver's capabilities
    - various message handlers: handle_xxx() (handle_timeout, handle_char)
    - refresh_strip() - to generate output for a row portion when asked
    '''

    def __init__ (self):
        '''
        Initializes the root window.
        Overload this!
        '''
        window.__init__(self)

    def generate_style_map (self, style_caps):
        '''
        Produces a mapping name -> style where styles should be adapted
        to given capabilities.
        Normally this is called when the app is getting connected to a driver
        after obtaining the style capabilities of the driver.

        '''
        default_style = style(
                attr = A_NORMAL,
                fg = style_caps.fg_default,
                bg = style_caps.bg_default)
        return dict(default = default_style)

    def loop (app, drv):
        '''
        Uses the given driver to display the app and receives events from it.
        No need to overload this.
        '''
        try:
            drv.register_styles(app.generate_style_map(drv.get_style_caps()))
            ss = drv.get_screen_size()
            app.resize(width = ss.width, height = ss.height)
            while True:
                drv.render(app.fetch_updates())
                app.handle(drv.get_message())
        except app_quit as e:
            return e.ret_code

def run (driver_runner, app):
    return driver_runner(lambda drv, app = app: app.loop(drv))

