import zlx.record
from collections import namedtuple

class error (RuntimeError):
    pass

class app_quit (error):
    def __init__ (self, ret_code = 0):
        error.__init__(self, 'quit tui app')
        self.ret_code = ret_code
    pass

screen_size = namedtuple('screen_size', 'width height'.split())

style_caps = namedtuple('style_caps', 'attr fg_count bg_count fg_default bg_default'.split())


#* message ******************************************************************
class message (object):
    '''
    Represents an event generated by a tui driver.
    A driver may derive this or use it as it is.
    '''
    def __init__ (self, **kw):
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
            self.style_map[k] = self.register_style(v)

    def register_style (self, style):
        return style

    def get_message (self):
        '''
        Overload this or else...
        '''
        return message('quit')


# attributes to be used in style (:-D all puns intended)
A_NORMAL = 0
A_BOLD = 1
A_ITALIC = 2
A_ALT_CHARSET = 4

#* style ********************************************************************
class style (zlx.record.Record):
    '''
    Describes the style for a portion of text.
    Instantiate with: style(fg, bg, attr)
    '''
    __slots__ = 'attr fg bg'.split()
    pass

class strip (zlx.record.Record):
    '''
    A strip is a portion of a one line of text with its style.
    '''
strip = zlx.record.make('tui.strip', 'text style col')

def text_width (text):
    return len(text)

#* window *******************************************************************
class window (object):
    '''
    A window has width and height and a list of updates.
    The updates are organized as a list for each row where elements are
    strips.
    '''

    def __init__ (self, width = 0, height = 0, default_style_name = 'default'):
        object.__init__(self)
        self.width = width
        self.height = height
        self.default_style_name = default_style_name
        self.wipe_updates()

    def wipe_updates (self):
        '''
        Empties the strips from the updates field.
        No need to overload this.
        '''
        self.updates = [[] for i in range(self.height)]

    def write (self, row, col, style, text):
        '''
        Adds the given text in the right place in the updates field.
        No need to overload this.
        '''
        self.updates[row]

    def refresh_strip (self, row, col, width):
        '''
        Refreshes the content a strip of the window.
        Overload this to implement displaying content in your window.
        Normally you want to call write() with text to cover all length
        of the given strip.
        This should ideally not do blocking operations as for good UX it must
        be fast.
        '''
        self.write(row, col, self.default_style, ' ' * width)

    def refresh (self,
            start_row = 0,
            start_col = 0,
            height = None,
            width = None):
        '''
        Calls refresh() for each row in given range.
        if height or width are left None they will cover the window to its
        border.
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
        No need to overload unless for some reason refreshing the entire
        content is not desired after a resize
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
        getattr(self, 'handle_' + msg.name)(msg)

    def fetch_updates (self):
        '''
        Extracts the updates from this window.
        No need to overload this
        '''
        u = self.updates
        self.wipe_updates()
        return u

class app (window):
    '''
    Represents a Text UI application.
    Derive to taste.
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
            ss = drv.get_screen_size()
            app.resize(width = ss.width, height = ss.height)
            while True:
                drv.render(app.fetch_updates())
                app.handle(drv.get_message())
        except app_quit as e:
            return e.ret_code

def run (driver_runner, app):
    return driver_runner(lambda drv, app = app: app.loop(drv))

