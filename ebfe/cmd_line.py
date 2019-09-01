import sys
import argparse

def cmd_test (cli):
    print('tests passed')

def cmd_edit (cli):
    if not cli.file:
        cli.ap.print_help()
        return
    #print('editing files: {!r}'.format(cli.file))
    import ebfe.tui
    ebfe.tui.main(cli)
    return

def main ():
    args = sys.argv[1:]

    ap = argparse.ArgumentParser(
            description = 'hex editor and binary formats inspector tool')
    ap.set_defaults(cmd='edit')
    ap.add_argument('-v', '--verbose', help = 'be verbose', 
            action = 'store_true', default = False)
    ap.add_argument('-t', '--test', dest = 'cmd', 
            action = 'store_const', const = 'test', help = 'run the tests')
    ap.add_argument('file', nargs = '*', help = 'input file(s)')

    cli = ap.parse_args(args)
    cli.ap = ap

    
    if cli.verbose: print('argv={!r} cli={!r}'.format(sys.argv, cli))

    globals()['cmd_' + cli.cmd](cli)



