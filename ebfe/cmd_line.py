import sys
import argparse
import ebfe.app

def cmd_test (cli):
    #if not cli.file:
    #    cli.ap.print_help()
    #    return
    #print('editing files: {!r}'.format(cli.file))
    import ebfe.tui
    x = []
    for s, t in ebfe.tui.styled_text_chunks('tra\abold\bla\aitalic\bla!\ameh\b'):
        x.append((s, t))
    print(repr(x))
    #import ebfe.old_tui
    #ebfe.old_tui.main(cli)
    return

def boot_driver_curses (cli):
    from ebfe.tui_curses import run
    return run

def boot_driver_mock (cli):
    raise RuntimeError('todo: mock driver')

def cmd_interactive_edit (cli):
    app = ebfe.app.main(cli)
    drv_runner = globals()['boot_driver_' + cli.tui_driver](cli)
    ebfe.tui.run(drv_runner, app)
    return

def main ():
    args = sys.argv[1:]
    ap = argparse.ArgumentParser(
            description = 'hex editor and binary formats inspector tool')
    ap.set_defaults(cmd='interactive_edit')
    ap.add_argument('-v', '--verbose', help = 'be verbose',
            action = 'store_true', default = False)
    ap.add_argument('-t', '--test', dest = 'cmd',
            action = 'store_const', const = 'test', help = 'run the tests')
    ap.add_argument('-d', '--tui-driver', metavar = 'DRIVER',
            dest = 'tui_driver', default = 'curses',
            help = 'select the TUI driver')
    ap.add_argument('file', nargs = '*', help = 'input file(s)')
    ap.add_argument('--load-delay SECONDS', dest = 'load_delay',
            type = float, default = 0,
            help = 'delay loads from files (for testing)')

    cli = ap.parse_args(args)
    cli.ap = ap


    if cli.verbose: print('argv={!r} cli={!r}'.format(sys.argv, cli))

    globals()['cmd_' + cli.cmd](cli)

if __name__ == '__main__':
    main()

