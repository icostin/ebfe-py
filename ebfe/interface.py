O = {
    'cfg': {
        'folder': '',
        'file': '',
    },

    # This is the function which quits the editor
    'quit': lambda: None,
    # This is the function which invokes global commands
    'cmd': lambda a,b: None,
    # This is the function which can be used to output text on the console
    'console_out': lambda text: None,
    # These functions are for adding characters to the status window
    'status_push': lambda ch: None,
    'status_pop': lambda: None,
    'status_empty': lambda: None,
    'status_get': lambda: None,
    'status_is_empty': lambda: None,
    'hexedit_goto': lambda a: None,
}

