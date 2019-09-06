import functools
import curses
import ebfe
import traceback
from zlx.io import emsg

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
    pair_seed = 1

    def __init__ (self, text = None):
        object.__init__(self)
        self.first_hl_name = None
        if text: self.parse(text)

    def add (self, name, 
            fg = 7, bg = 0, attr = curses.A_NORMAL, 
            fg256 = None, bg256 = None, attr256 = None):
        '''adds a tui attribute'''

        if curses.COLORS == 256:
            if fg256 is not None: fg = fg256
            if bg256 is not None: bg = bg256
            if attr256 is not None: attr = attr256

        pair = self.__class__.pair_seed
        self.__class__.pair_seed += 1

        curses.init_pair(pair, fg, bg)
        #emsg('pair={} fg={} bg={}', pair, fg, bg)
        v = attr | curses.color_pair(pair)
        if not self.first_hl_name: self.first_hl_name = name
        setattr(self, name, v)

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
                  box_title="",
                  hl_set = None):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.attr = attr
        self.background = background
        self.has_border = box
        self.box_title = box_title
        self.hl_set = hl_set

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

    def add_hl_text (self, hl_text, x = None, y = None, x2 = 0, hl_begin = '<<', hl_end = '>>', hl_set = None):
        if hl_set is None: self.hl_set
        if x is None or y is None:
            xx, yy = self.window.getyx()
            if x is None: x = xx
            if y is None: y = yy
        active_hl = hl_set.first_hl_name
        for line in hl_text.splitlines():
            for hs in ''.join((active_hl, hl_end, line)).split(hl_begin):
                active_hl, text = hs.split(hl_end, 1)
                self.window.attrset(getattr(hl_set, active_hl))
                try:
                    if x is not None:
                        self.window.addstr(y, x, text)
                        x = None
                    else:
                        self.window.addstr(text)
                except:
                    traceback.print_tb()
                    return
            x = x2
            y = y + 1

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

        w4 = self.add_window(32, 18, 40, 20, box=True)
        if w4:
            #w4.addstr(2, 0, "High five!")
            w4.add_hl_text('''
<<title>> The Islander <<normal>>

<<first>>An<<normal>> old man by a seashore
At the end of day
Gazes the horizon
With seawinds in his face<<sign>>.<<normal>>
Tempest<<sign>>-<<normal>>tossed island<<sign>>,<<normal>>
Seasons all the same<<sign>>,<<normal>>
Anchorage unpainted<<sign>>,<<normal>>
And a ship without a <<last>>name<<sign>>...

'''.strip(),
                x = 4, y = 1, x2 = 2, 
                hl_set = tui_hl_set('''
normal fg=grey bg=black attr=normal
first fg=yellow bg=black attr=bold
last fg=cyan bg=black attr=bold
title fg=yellow bg=blue attr=bold
sign fg=red bg=black attr=bold
'''))
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
        self.scr.getkey()


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

