import curses


def run (stdscr, cli):
    curses.start_color()
    stdscr.clear()

    curses.init_pair(1, curses.COLOR_RED, curses.COLOR_WHITE)
    curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLACK)


    for i in range(len(cli.file)):
        stdscr.addstr(i + 2, 0, repr(cli.file[i]))
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

