import functools
import curses

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

class tui (object):
    '''
    main text-ui object holding the state of all interface objects
    '''

    def __init__ (self, stdscr, cli):
        object.__init__(self)
        self.hl = tui_hl_set(DEFAULT_HIGHLIGHTING)
        self.scr = stdscr
        self.cli = cli

    def run (self):
        self.scr.clear()
        self.scr.bkgd('.', self.hl.normal_text)
        self.scr.addstr(1, 0, 'colors: {}, color pairs: {}.'.format(curses.COLORS, curses.COLOR_PAIRS))
        self.scr.refresh()
        for i in range(len(self.cli.file)):
            self.scr.addstr(i + 2, 0, 'input file #{}: {!r}'.format(i + 1, self.cli.file[i]))
        w = curses.newwin(1, curses.COLS, 0, 0)
        w.bkgd(' ', self.hl.normal_title)
        w.addstr(0, 0, 'ebfe - ver 0.00')
        w.refresh()
        self.scr.getkey()



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

def main (cli):
    return curses.wrapper(run, cli)

