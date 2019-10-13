import functools
from collections import namedtuple

import zlx.record
from zlx.io import dmsg

def saturate (x, min_value, max_value):
    return max(min(x, max_value), min_value)

#* error ********************************************************************
class error (RuntimeError):
    def __init__ (self, fmt, *a, **b):
        RuntimeError.__init__(self, fmt.format(*a, **b))

#* app_quit *****************************************************************
class app_quit (error):
    def __init__ (self, ret_code = 0):
        error.__init__(self, 'quit tui app')
        self.ret_code = ret_code

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
# class message
    def __init__ (self, *l, **kw):
        object.__init__(self)
        if l:
            for i in range(len(l)):
                setattr(self, self.__slots__[i], l[i])
        for k, v in kw.items():
            setattr(self, k, v)
# class message - end

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
# class driver
    def __init__ (self):
        object.__init__(self)

# class driver
    def get_screen_size (self):
        raise RuntimeError('must be implemented in derived class')

# class driver
    def get_style_caps (self):
        '''
        Overload this to return the capabilites for styles.
        The function should return a style_caps object
        '''
        return style_caps(A_NORMAL, 1, 1, 0, 0)

# class driver
    def register_styles (self, style_map):
        '''
        Processes the given map and for each style calls register_style()
        storing the returned object.
        No need to overload this.

        '''
        self.style_map = {}
        for k, v in style_map.items():
            self.style_map[k] = self.build_style(v)

# class driver
    def build_style (self, style):
        '''
        Process the tui attributes and colors and generate whatever is needed
        by the driver to display text with those specs.
        Overload this!
        '''
        return style

# class driver
    def get_message (self):
        '''
        Overload this or else...
        '''
        return message('quit')

# class driver
    def render (self, updates):
        '''
        Goes through all update strips and renders them.
        No need to overload this.
        '''
        show_focus = False
        focus_row = 0
        focus_col = 0
        dmsg('driver: {} updates', len(updates))
        for row, strips in updates.items():
            for s in strips:
                if len(s.text) > 0:
                    self.render_text(s.text, s.style_name, s.col, row)
                    #if not show_focus and s.text[0] == '*' and s.style_name == 'test_focus':
                    if s.text[0] == '*' and s.style_name == 'test_focus':
                        show_focus = True
                        focus_row = row
                        focus_col = s.col
                        dmsg("RENDER FOCUS CHAR POSITION -> row: {}, s_col: {}, text: {}, style: {}", row, s.col, s.text[:1], s.style_name)
        if show_focus:
            self.render_text('*', 'test_focus', focus_col, focus_row)

# class driver
    def render_text (self, text, style_name, column, row):
        '''
        Overload this to output.
        '''
        pass

# class driver - end


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

def generate_style_markers (styles_desc):
    m = {}
    dflt = None
    dflt_value = None
    for s in styles_desc.split():
        if '=' in s: a, b = s.split('=', 1)
        else: a, b = s, s
        if not dflt:
            dflt = a
            dflt_value = b
        m[a] = ''.join((STYLE_BEGIN, b, STYLE_END))
    m[None] = dflt_value
    return m

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

    wid_seed = 0

# class window
    def __init__ (self, wid = None, width = 0, height = 0, styles = 'default', can_have_focus = False, show = True):
        object.__init__(self)
        if wid is None:
            wid = '{}_{}'.format(self.__class__.__name__, window.wid_seed)
            window.wid_seed += 1
        self.wid = wid
        self.width = width
        self.height = height
        self.can_have_focus = can_have_focus
        self.show = show
        self.in_focus = False
        self.render_starting_line = -1
        self.render_starting_column = 0
        self.wipe_updates()
        self.set_styles(styles)

# window.__str__()
    def __str__ (self):
        return self.wid

# window.__repr__()
    def __repr__ (self):
        return self.wid

# class window
    def set_styles (self, styles):
        self.style_markers = generate_style_markers(styles + ' test_focus')
        self.default_style_name = self.style_markers[None]

# class window
    def subwindows (self):
        return tuple()

# class window
    def wipe_updates (self):
        '''
        Empties the strips from the updates field.
        No need to overload this.
        '''
        self.updates = {}

# class window
    def write_ (self, row, col, style_name, text):
        '''
        Adds the given text in the right place in the updates field.
        No need to overload this.
        '''
        if row not in self.updates:
            self.updates[row] = []
        self.updates[row].append(strip(text, style_name, col))
        #dmsg('win={!r}({}x{}) write strip: row={} col={} style={!r} text={!r}', self, self.width, self.height, row, col, style_name, text)

# class window
    def write (self, row, col, style_name, text, clip_col = 0, clip_width = None):
        '''
        Adds the given text taking into account the given clipping coords.
        No need to overload this.
        '''
        if not self.show: return

        # limit clipping coords to window width
        clip_end_col = clip_col + clip_width if clip_width is not None else self.width
        if clip_col < 0: clip_col = 0
        if clip_end_col > self.width: clip_end = self.width
        if clip_col >= clip_end_col: return

        if col < clip_col:
            i = compute_index_of_column(text, clip_col - col)
            if i is None: return
            col = clip_col
            text = text[i:]
        #clip_end_col = clip_col + clip_width if clip_width is not None else self.width
        #if clip_end_col > self.width: clip_end_col = self.width
        if col >= clip_end_col: return
        i = compute_index_of_column(text, clip_end_col - col)
        if i is not None: text = text[:i]
        self.write_(row, col, style_name, text)

# class window
    def sfmt (self, fmt, *l, **kw):
        '''
        Format text with styles.
        '''
        return fmt.format(*l, **kw, **self.style_markers)

# class window
    def put (self, row, col, styled_text, clip_col = 0, clip_width = None):
        #dmsg("************* put self: {}, row: {}, col: {}, clip_col: {}, clip_width: {}", self, row, col, clip_col, clip_width)
        for style, text in styled_text_chunks(styled_text, self.default_style_name):
            self.write(row, col, style, text, clip_col, clip_width)
            col += compute_text_width(text)

# class window
    def integrate_updates (self, row_delta, col_delta, updates):
        for row in updates:
            for s in updates[row]:
                self.write_(row + row_delta, s.col + col_delta, s.style_name, s.text)

# class window
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

# class window
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
        dmsg('win:{} refresh', self)
        if not self.show:
            return

        if start_row >= self.height or start_col >= self.width: return

        if height is None: height = self.height
        if width is None: width = self.width

        end_row = min(self.height, start_row + height)
        width = min(self.width - start_col, width)

        for r in range(start_row, end_row):
            self.refresh_strip(r, start_col, width)

# class window
    def resize (self, width = None, height = None):
        '''
        Updates window size and refreshes whole content.
        Do not overload this. If you need to adjust internal layout following
        a resize please overload on_resize()
        '''
        if width is None: width = self.width
        if height is None: height = self.height
        self.width = max(0, width)
        self.height = max(0, height)
        dmsg('win:{} resize to {}x{}', self, self.width, self.height)
        if self.width > 0 and self.height > 0:
            self.on_resize(self.width, self.height)

# class window
    def on_resize (self, width, height):
        '''
        Overload this if you need more than just a refresh of the content
        '''
        self.refresh()

# class window
    def handle (self, msg):
        '''
        Message handler.
        No need to overload this, instead create/overload methods named
            handle_<message_name>
        '''
        handler_name = 'handle_' + msg.name
        if hasattr(self, handler_name):
            getattr(self, handler_name)(msg)

# class window
    def handle_resize (self, msg):
        '''
        Default handler for window resize!
        '''
        self.resize(msg.width, msg.height)

# class window
    def fetch_updates (self):
        '''
        Extracts the updates from this window.
        No need to overload this
        '''
        u = self.updates
        self.wipe_updates()
        return u

# class window
    def is_focusable (self):
        return self.can_have_focus

# class window
    def set_focusable (self, focusable = True):
        self.can_have_focus = focusable
        return

    def focus_to (self, win):
        if self is win:
            dmsg('{} focusing!', self)
            self.focus()
            return True
        dmsg('{}.focus_to({}) -> false', self, win)
        return False

# class window
    def focus (self, is_it = True):
        '''
        It can switch from being in focus to out of focus
        if the focusing mechanism is enabled (disabled by default)
        It will always be able to switch out of focus!
        '''
        dmsg('{}: new_focus={} old_focus={} can_focus={} show={}',
                self, is_it, self.in_focus, self.can_have_focus, self.show)
        new_focus_state = is_it and self.can_have_focus and self.show
        if self.in_focus == new_focus_state:
            dmsg('{}: already in focus={}', self, new_focus_state)
            return
        dmsg('{}.focus = {}. state: {!r}', self, new_focus_state, self)
        self.in_focus = new_focus_state
        self.on_focus_change()

# class window
    def on_focus_change (self):
        '''
        Called when focus state changes.
        Can override this or override both on_focus_enter(), on_focus_leave()
        '''
        if self.in_focus:
            self.on_focus_enter()
        else:
            self.on_focus_leave()

# class window
    def on_focus_enter (self):
        return

# class window
    def on_focus_leave (self):
        return

# window.input_timeout()
    def input_timeout (self):
        '''
        Calls on_input_timeout on self.
        '''
        dmsg('{}.input_timeout()', self)
        self.on_input_timeout()

    def on_input_timeout (self):
        '''
        Overload this to handle input timeout.
        If a window has subwindows overload this to pass down to subwindows.
        '''
        return

# class window - end

#* container ****************************************************************
class container (window):
    '''
    Container for storing multiple windows on a direction (h/v).
    '''

    HORIZONTAL = 0
    VERTICAL = 1
    item = zlx.record.make('container.item', 'window weight min_size max_size concealed index pos size')

# class container
    def __init__ (self, direction = VERTICAL, wid = None):
        window.__init__(self, wid = wid, can_have_focus = True)
        assert direction in (container.HORIZONTAL, container.VERTICAL)
        self.direction = direction
        self.items = []
        self.focused_item_index = None
        self.win_to_item_ = {}

# container.__repr__()
    def __repr__ (self):
        return '{}(focus_idx={}, items={!r})'.format(self, self.focused_item_index, self.items)

# class container
    def subwindows (self):
        for item in self.items:
            yield item.window
        return

    def _update_item_indices (self, start = 0):
        for i in range(start, len(self.items)):
            self.items[i].index = i

# container.add()
    def add (self, win, index = None, weight = 1, min_size = 1, max_size = 65535, concealed = False):
        assert weight > 0
        assert min_size <= max_size

        if index is None: index = len(self.items)

        item = container.item(win, weight, min_size, max_size, concealed, index)
        dmsg('{}.add({!r})', self, item)
        self.items.insert(index, item)
        self.win_to_item_[win] = item

        self._update_item_indices(index + 1)

        if self.focused_item_index is not None and index <= self.focused_item_index:
            self.focused_item_index += 1

        if not concealed:
            self.resize()

        dmsg('state after container.add(): {!r}', self)
        return item

# container.set_item_visibility()
    def set_item_visibility (self, win, visible = True, toggle = False):
        item = self.win_to_item_[win]
        if toggle:
            concealed = not item.concealed
        else:
            concealed = not visible
        if item.concealed == concealed:
            dmsg('{}.set_item_visibility({},v={},t={}) => leaving {} unchanged',
                    self, win, visible, toggle, win)
            return

        # if concealing focused item, move focus
        if self.focused_item_index == item.index and concealed:
            dmsg('{}.set_item_visibility({}) => concealing focused item... cycle focus',
                    self, win)
            dmsg('state: {!r}', self)
            self.cycle_focus(in_depth = False, wrap_around = True)
        dmsg('{}.set_item_visibility({}) => visible={}, resizing...',
                self, win, not concealed)
        item.concealed = concealed
        self.resize()
        return

# class container
    def _locate_item (self, pos):
        for i in range(len(self.items)):
            item = self.items[i]
            if pos >= item.pos and pos - item.pos < item.size:
                return (item, i)
        return (None, None)

# container.del_at_index()
    def del_at_index (self, idx):
        if idx >= len(self.items): raise error('boo')
        if self.focused_item_index > idx:
            self.focused_item_index -=1
        del self.items[idx]
        self._update_item_indices(idx)

# class container
    def is_horizontal (self):
        return self.direction == container.HORIZONTAL

# class container
    def is_vertical (self):
        return self.direction == container.VERTICAL

# class container
    def _forget_item_locations (self):
        for item in self.items:
            item.pos = 0
            item.size = 0

# class container
    def _compute_weight_of_unsized_items (self):
        weight = 0
        for item in self.items:
            if item.concealed: continue
            weight += item.weight
        return weight

# class container
    def _compute_min_size (self):
        min_size = 0
        for item in self.items:
            if item.concealed: continue
            min_size += item.min_size
        return min_size

# class container
    def _compute_position_of_items (self):
        pos = 0
        for item in self.items:
            item.pos = pos
            pos += item.size

# class container
    def is_focusable (self):
        if not self.can_have_focus: return False
        for item in self.items:
            if item.window.is_focusable(): return True

# class container
    def get_focused_item (self):
        if self.focused_item_index is None: return None
        assert self.focused_item_index < len(self.items)
        assert not self.items[self.focused_item_index].concealed
        return self.items[self.focused_item_index]

# class container
    def on_focus_leave (self):
        dmsg('{}.on_focus_leave: focused_index={}', self, self.focused_item_index)
        if self.focused_item_index is not None:
            item = self.items[self.focused_item_index]
            item.window.focus(False)
            u = item.window.fetch_updates()
            dmsg('{}.on_focus_leave: removed focus from {} => {} updates', self, item.window, len(u))
            self.integrate_updates(*self.get_item_row_col(item), u)

# class container
    def on_focus_enter (self):
        dmsg('{}.on_focus_enter', self)
        if (self.focused_item_index is not None and
            (self.focused_item_index >= len(self.items) or
             not self.items[self.focused_item_index].window.is_focusable())):
            self.focused_item_index = None
        if self.focused_item_index is None:
            self.cycle_focus()
        else:
            item = self.items[self.focused_item_index]
            item.window.focus()
            self.integrate_updates(*self.get_item_row_col(item), item.window.fetch_updates())

# container.focus_to()
    def focus_to (self, win):
        dmsg('{}: requested to focus on {}', self, win)
        if window.focus_to(self, win): return True
        for i in range(len(self.items)):
            if self.items[i].window.focus_to(win):
                dmsg('{}: item #{} focused! prev_focused_index={}',
                        self, i, self.focused_item_index)
                if (self.focused_item_index is not None and
                        self.focused_item_index != i):
                        item = self.items[self.focused_item_index]
                        item.window.focus(False)
                        self.integrate_updates(*self.get_item_row_col(item), item.window)
                self.focused_item_index = i
                dmsg('{}.focused_item_index = {}', self, i)
                item = self.items[i]
                self.integrate_updates(*self.get_item_row_col(item), item.window.fetch_updates())
                self.in_focus = True
                return True
        return False

# class container
    def get_item_row_col (self, item):
        if self.is_vertical(): return (item.pos, 0)
        elif self.is_horizontal(): return (0, item.pos)

# class container
    def cycle_focus (self, in_depth = True, wrap_around = False):
        dmsg('{}.cycle_focus: focused_index={}', self, self.focused_item_index)
        if self.focused_item_index is not None:
            item = self.items[self.focused_item_index]
            if in_depth and hasattr(item.window, 'cycle_focus'):
                dmsg('{}: try cycle_focus on subitem: {!r}', self, item)
                if item.window.cycle_focus(in_depth = True):
                    self.integrate_updates(*self.get_item_row_col(item), item.window.fetch_updates())
                    return True
            dmsg('{} - remove focus for {!r}', self, item)
            item.window.focus(False)
            self.integrate_updates(*self.get_item_row_col(item), item.window.fetch_updates())
        n = len(self.items)
        s = 0 if self.focused_item_index is None else self.focused_item_index + 1
        dmsg('{}.cycle_focus: s={} items={!r}', self, s, self.items)
        for i in range(s, n):
            item = self.items[i]
            if not item.concealed and item.window.is_focusable():
                self.focused_item_index = i
                dmsg('{} - set focus for {!r}', self, item)
                item.window.focus(True)
                self.integrate_updates(*self.get_item_row_col(item), item.window.fetch_updates())
                return True
        self.focused_item_index = None
        dmsg('{} - removing focused_item_index', self)
        if wrap_around: return self.cycle_focus(in_depth = in_depth, wrap_around = False)
        return False

# class container
    def size_to_weight_height (self, size):
        if self.direction == container.HORIZONTAL: return (size, self.height)
        elif self.direction == container.VERTICAL: return (self.width, size)
        else: raise error('bad dir: {}', self.direction)

# class container
    def on_resize (self, width, height):
        if self.direction == container.HORIZONTAL: size = width
        elif self.direction == container.VERTICAL: size = height
        else: raise error('bad dir: {}', self.direction)

        self._forget_item_locations()
        min_size = self._compute_min_size()
        dmsg('{} resize({}x{}): min_size={} size={}',
                self, width, height, min_size, size)
        if size < min_size:
            focused_item = self.get_focused_item()
            if focused_item:
                focused_item.size = min(size, focused_item.max_size)

        items_to_place = [item for item in self.items if not item.concealed]
        items_to_place.sort(key = lambda item: item.max_size - item.min_size)

        total_weight = self._compute_weight_of_unsized_items()
        for item in items_to_place:
            dmsg('{}: {!r} => iw={} tw={}', self, item, item.weight, total_weight)
            item.size = saturate(round(size * item.weight / total_weight), item.min_size, item.max_size)
            size -= item.size
            total_weight -= item.weight

        self._compute_position_of_items()

        lp = 0
        for item in self.items:
            if item.concealed: continue
            wh = self.size_to_weight_height(item.size)
            dmsg('{}: resizing {!r} to {}', self, item, wh)
            item.window.resize(*wh)
            rc = self.get_item_row_col(item)
            u = item.window.fetch_updates()
            dmsg('{}: integrating {} updates from {!r} at {}', self, len(u), item, rc)
            self.integrate_updates(*rc, u)
            lp = item.pos + item.size

        if lp < size: self.refresh()

        return

# container.input_timeout()
    def input_timeout (self):
        self.on_input_timeout()
        for item in self.items:
            item.window.input_timeout()
            if not item.concealed:
                self.integrate_updates(*self.get_item_row_col(item),
                        item.window.fetch_updates())

# class container
    def refresh_strip (self, row, col, width):
        dmsg('{}.refresh_strip(row={}, col={}, width={})', self, row, col, width)
        if self.is_vertical():
            item, idx = self._locate_item(row)
            if item:
                item.window.refresh_strip(row - item.pos, col, width)
                u = item.window.fetch_updates()
                self.integrate_updates(item.pos, 0, u)
                return
        elif self.is_horizontal():
            item, idx = self._locate_item(col)
            end_col = col + width
            while col < end_col and item:
                w = min(item.size, width)
                item.window.refresh_strip(row, col - item.pos, w)
                self.integrate_updates(0, item.pos, item.window.fetch_updates())
                col += item.size
                width -= w
                idx += 1
                item = self.items[idx] if idx < len(self.items) else None
            # if not covered 'til end fall in the default window refresh
        if width:
            window.refresh_strip(self, row, col, width)
        return

# container.handle_keystate()
    def handle_keystate (self, msg):
        item = self.get_focused_item()
        if item:
            item.window.handle_keystate(msg)
            self.integrate_updates(*self.get_item_row_col(item),
                    item.window.fetch_updates())
        else:
            dmsg('{}: dropping {!r} due to unfocused item', self, msg)

# class container - end

#* vcontainer ***************************************************************
def vcontainer (**b):
    return container(direction = container.VERTICAL, **b)

#* hcontainer ***************************************************************
def hcontainer (**b):
    return container(direction = container.HORIZONTAL, **b)

#* cc_window ****************************************************************
class cc_window (window):
    '''
    Cached-content window.
    This window caches the content that needs displaying.
    When refresh() or refresh_strip() is called it just
    provides the relevant portion of the cache.
    '''

# class cc_window
    def __init__ (self, wid = None, init_content = None, width = 0, height = 0, styles = 'default'):
        window.__init__(self, wid, width, height, styles)
        self.content = []
        self.top_row = 0
        if init_content: self.set_content(0, init_content)

# class cc_window
    def set_content (self, row, text):
        '''updates the cached content. No need to overload this!'''
        l = text.splitlines()
        while row > len(self.content):
            self.content.append('')
        self.content[row : row + len(l)] = l
        dmsg('got content:\n{}', '\n'.join([repr(x) for x in self.content]))

# class cc_window
    def scroll (self, delta, absolute = False):
        if absolute: self.top_row = 0
        self.top_row += delta

# class cc_window
    def refresh_strip (self, row, col, width):
        dmsg('cc_win: refresh row={} col={} width={}', row, col, width)
        logical_row = self.top_row + row
        if logical_row >= 0 and logical_row < len(self.content):
            txt = self.sfmt(self.content[logical_row])
        else:
            txt = ''
        dmsg('{}: cc_win: refresh_strip with {!r}', self, txt)
        w = compute_styled_text_width(txt)
        if w < self.width: txt += self.sfmt(' ' * (self.width - w))
        self.put(row, 0, txt, clip_col = col, clip_width = width)

# class cc_window
    def regenerate_content (self):
        '''
        Overload this if reflowing text is needed
        '''
        pass

# class cc_window
    def on_resize (self, width, height):
        self.regenerate_content()
        self.refresh()

# end cc_window

#* application **************************************************************
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

# application.__init__()
    def __init__ (self):
        '''
        Initializes the root window.
        Overload this!
        '''
        window.__init__(self)

# application.generate_style_map()
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

# application.loop()
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

# application.handle_timeout()
    def handle_timeout (self, msg):
        self.input_timeout()

# class application - end

#* run **********************************************************************
def run (driver_runner, app):
    return driver_runner(lambda drv, app = app: app.loop(drv))

