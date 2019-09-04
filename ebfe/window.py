"""
Generic curses window class
Coordinates order is the correct one : x, y, width, height
"""

import curses

#----------------------------------------------------------------
class window_manager ():

    def __init__ (self):
        self.window_list = []

    def add_window (self, x=0, y=0, 
                  w=curses.COLS, h=curses.LINES,
                  attr=curses.A_NORMAL,
                  background=" ", box=False,
                  box_title=""):
        w = window(x, y, w, h, attr, background, box, box_title)
        if w:
            w.sync()
            self.window_list.append(w)
        return w

    # Refreshes the screen and updates windows content
    def refresh (self):
        curses.doupdate()

#----------------------------------------------------------------
class window ():
    """
    Most of __init__ parameters have default values
    If a window is created with a border then two windows are actually created:
     - A parent one will hold the border
     - A secondary relative window which will hold the actual content 
       (to allow wrapping and not ruin the actual border)
    """
    def __init__ (self, x=0, y=0, 
                  w=curses.COLS, h=curses.LINES,
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
            self.box = curses.newwin(h, w, y, x)
            self.window = self.box.derwin(h-2, w-2, 1, 1)
        else:
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

