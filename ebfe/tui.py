import functools
import curses

#-----------------------------------------------------------------------------
class tui_hl_set (object):
    '''
    TUI attribute set.
    Holds an attribute for each TUI element we need displaying.
    '''
    PARSE_MAP = dict(
            normal = curses.A_NORMAL,
            bold = curses.A_BOLD,
            black = 0,
            red = 1,
            green = 2,
            yellow = 3,
            blue = 4,
            magenta = 5,
            cyan = 6,
            grey = 7,
            )
    def __init__ (self, text = None):
        object.__init__(self)
        self.reset()
        if text: self.parse(text)

    def reset (self):
        self.pair_seed = 1
    
    def add (self, name, 
            fg = 7, bg = 0, attr = curses.A_NORMAL, 
            fg256 = None, bg256 = None, attr256 = None):
        '''adds a tui attribute'''

        if curses.COLORS == 256:
            if fg256 is not None: fg = fg256
            if bg256 is not None: bg = bg256
            if attr256 is not None: attr = attr256

        pair = self.pair_seed
        self.pair_seed += 1

        curses.init_pair(pair, fg, bg)
        setattr(self, name, attr | curses.color_pair(pair))

    def parse (self, text):
        for line in text.splitlines():
            if '#' in line: line = line[0:line.index('#')]
            line = line.strip()
            if line == '': continue
            name, *attrs = line.split()
            d = {}
            for a in attrs:
                k, v = a.split('=', 1)
                vparts = (self.PARSE_MAP[x] if x in self.PARSE_MAP else int(x) for x in v.split('|'))
                d[k] = functools.reduce(lambda a, b: a | b, vparts)
            self.add(name, **d)


DEFAULT_HIGHLIGHTING = '''
normal_title fg=red bg=grey attr=bold
normal_status fg=black bg=grey 
normal_text fg=grey bg=blue
'''

#-----------------------------------------------------------------------------
"""
It's handling and translating input into commands
Will repaint the screen on receiving display commands
"""
class displayinput ():
    def __init__ (self, stdscr):
        self.scr = stdscr
        self.scr.clear()
        #self.scr.bkgd(' ', self.hl.normal_text)
        self.scr.refresh()
        self.scr.addstr(1, 0, 'colors: {}, color pairs: {}.'.format(curses.COLORS, curses.COLOR_PAIRS))
        # Make waiting for input non-blocking
        self.scr.nodelay(True)


    def get_display_size ():
        return (curses.COLS, curses.LINES)

    # Returns a tuple containing the state of ALT/escape key and the translated input
    # wait for 0.1 seconds before returning None if no key was pressed
    def get_input (self):
        esc = False
        curses.halfdelay(1)
        
        try:
            #c = self.scr.getkey()
            c = self.scr.getkey()
            # is it ESC or ALT+KEY ?
            if c == '\x1b':
                esc = True
                c = self.scr.getkey()
            return (esc, c)

        except curses.error:
            self.scr.addstr(22, 0, '{}'.format(curses.error))
            if esc:
                return (False, 'ESC')
            else:
                return None

    def display (self, x, y, text):
        self.scr.addstr(y, x, text)
        self.scr.noutrefresh()

    # Refreshes the screen and updates windows content
    def refresh (self):
        curses.doupdate()

#-----------------------------------------------------------------------------
"""
A container for window objects which will virtually fill all available space
Its children (containers) would be stacked on H or V axes
It can only have one associated window
"""
class container ():
    def __init__ (self, parent=None,
                  wp=100.0, hp=100.0,
                  resizable=False):
        self.parent = parent
        self.resizable = resizable
        self.wp = wp
        self.hp = hp
        self.w = 0
        self.h = 0
        self.window = None
        self.children = []

    def set_window (self, win):
        self.window = win

    def add_child (self, w=100.0, h=100.0, resizable=False):
        c = container(self, w, h, resizable)
        self.children.append(c)
        return c

    def dbg_display (self, scr, indent=0):
        scr.addstr('\n' + indent*'    ' + 'Container: w%={}, h%={}, (w:{}, h:{})'.format(self.wp, self.hp, self.w, self.h))
        if len(self.children) > 0: indent += 1
        for c in self.children:
            c.dbg_display(scr, indent)

    def resize (self, scr_w=0, scr_h=0, carry_w=0, carry_h=0):
        if scr_w <= 0 or scr_h <= 0:
            return

        self.w = round((scr_w * self.wp)/100.0)
        if self.resizable:
            self.w -= carry_w
            carry_w = 0
        if self.w <= 0:
            self.w = 1
            carry_w = 1

        self.h = round((scr_h * self.hp)/100.0)
        if self.resizable:
            self.h -= carry_h
            carry_h = 0
        if self.h <= 0:
            self.h = 1
            carry_h = 1

        for c in self.children:
            c.resize(self.w, self.h, carry_w, carry_h)
        
#-----------------------------------------------------------------------------
class window ():
    """
    Most of __init__ parameters have default values
    If a window is created with a border then two windows are actually created:
     - A parent one will hold the border
     - A secondary relative window which will hold the actual content 
       (to allow wrapping and not ruin the actual border)
    """
    def __init__ (self, x=0, y=0, 
                  w=0, h=0,
                  attr=curses.A_NORMAL,
                  background=" ", box=False,
                  box_title=""):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.attr = attr
        self.background = background
        self.has_border = box
        self.box_title = box_title

        # If it should have a border then we create the parent window
        if box:
            # There is not enough space for the border
            if h <= 2 or w <= 2:
                raise ValueError('Window size invalid! Not enough space for border', str(h), str(w))
                return
            self.box = curses.newwin(h, w, y, x)
            self.window = self.box.derwin(h-2, w-2, 1, 1)
        else:
            # invalid width and/or height
            if h <= 0 or w <= 0:
                raise ValueError('Window size invalid!', str(h), str(w))
                return
            self.box = None
            self.window = curses.newwin(h, w, y, x)

        # In the parent window we add the box and the title (if any)
        if self.box:
            #self.window.bkgd(self.background)
            self.box.bkgdset(self.background, self.attr)
            self.box.clear()
            self.box.box()
            if self.box_title != "":
                self.box.addstr(0, 2, "[ "+self.box_title+" ]")

        # The actual window we just clear it
        if self.window:
            self.window.bkgdset(self.background, self.attr)
            self.window.clear()

        # Update the internal buffers but not the screen yet
        self.sync()

    # Updates the text in the window buffer but doesn't refresh the screen
    def sync (self):
        if self.box:
            self.box.noutrefresh()
        if self.window:
            self.window.noutrefresh()

    # Wrapper for the original curses function with the parameters in correct order x, y
    def addstr (self, x, y, text):
        if self.window:
            self.window.addstr(y, x, text)

#-----------------------------------------------------------------------------
class tui (object):
    '''
    main text-ui object holding the state of all interface objects
    '''

    def __init__ (self, stdscr, cli):
        object.__init__(self)
        self.hl = tui_hl_set(DEFAULT_HIGHLIGHTING)
        self.scr = stdscr
        self.cli = cli
        self.window_list = []

    def add_window (self, x=0, y=0, 
                  w=0, h=0,
                  attr=curses.A_NORMAL,
                  background=" ", box=False,
                  box_title=""):
        # Can throw an exception if values are weird
        try:
            win = window(x, y, w, h, attr, background, box, box_title)
            if win and w > 0 and h > 0:
                win.sync()
                self.window_list.append(win)
                return win

        except ValueError as err:
            print(err.args)
        
        return None

    # Refreshes the screen and updates windows content
    def refresh (self):
        curses.doupdate()

    def run (self):
        self.scr.clear()
        self.scr.bkgd(' ', self.hl.normal_text)
        self.scr.refresh()

        self.scr.addstr(1, 0, 'colors: {}, color pairs: {}.'.format(curses.COLORS, curses.COLOR_PAIRS))
        for i in range(len(self.cli.file)):
            self.scr.addstr(i + 2, 0, 'input file #{}: {!r}'.format(i + 1, self.cli.file[i]))
       
        master = container()
        top_bar = master.add_child(100.0, 0.0)         # 0.1 should mean 1 line
        middle = master.add_child(100.0, 90.0, True)
        status = master.add_child(100.0, 10.0, True)
        mid_hex = middle.add_child(70.0, 100.0, True)
        mid_info = middle.add_child(30.0, 100.0, True)
        master.resize(curses.COLS, curses.LINES)
        master.dbg_display(self.scr)

        di = displayinput(self.scr)

        w1 = self.add_window(0, 0, curses.COLS, 1, self.hl.normal_title)
        if w1:
            w1.addstr(0, 0, 'ebfe - ver 0.01')
            w1.sync()

        w2 = self.add_window(10, 15, curses.COLS-20, 1, self.hl.normal_title)
        if w2:
            w2.addstr(2, 0, 'Another one-line window here just for lolz')
            w2.sync()

        w3 = self.add_window(1, 5, curses.COLS-2, 6, self.hl.normal_status, box=True, box_title="Weird Window Title")
        if w3:
            w3.addstr(0, 0, 'Some status here...hmmmmm')
            w3.sync()
            w3.addstr(0, 3, '|------> Seems to be working just fine at this time :-)')
            w3.sync()

        w4 = self.add_window(32, 18, 40, 10, box=True)
        if w4:
            w4.addstr(2, 2, "High five!")
            w4.sync()

        w5 = self.add_window(40, 25, 1, 10, box=True)
        if w5:
            w5.addstr(0, 0, "Exception :-/")
            w5.sync()

        self.refresh()
        #w = curses.newwin(1, curses.COLS, 0, 0)
        #w.bkgd(' ', self.hl.normal_title)
        #w.addstr(0, 0, 'ebfe - ver 0.00')
        #w.refresh()
        
        #self.scr.getkey()
        while(True):
            received_input = di.get_input()
            if received_input:
                di.display(0, 20, 'Input: {}        '.format(received_input))
                di.refresh()
                if received_input[1] == 'Q' or received_input[1] == 'q':
                    break

#-----------------------------------------------------------------------------
def run (stdscr, cli):
    return tui(stdscr, cli).run()
    stdscr.clear()

    curses.init_pair(1, curses.COLOR_RED, curses.COLOR_WHITE)
    curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLACK)



    stdscr.refresh()
    w = curses.newwin(1, curses.COLS, 0, 0)
    w.clear()
    w.bkgd(' ', curses.color_pair(1))
    w.addstr(0, 0, 'ebfe - ver 0.00')
    w.refresh()
    
    stdscr.getkey()
    return

#-----------------------------------------------------------------------------
def main (cli):
    return curses.wrapper(run, cli)

