import sys
import argparse
import uvicorn
from . import conf
from . import cmd_manager


def parse_config(args):
    parser = argparse.ArgumentParser(description="servecmd, serve command line via HTTP.")
    parser.add_argument("--config", default="", help="Config file.")
    parser.add_argument("--no-clean", action="store_true", help="Do not clean the job directory.")
    parser.add_argument('-v', '--verbose', action='count', default=0,
                        help='Vebosity (can be used multiple times)')
    parser.add_argument('--version',
                        action='store_true',
                        help='Show version information and quit')
    sub_parsers = parser.add_subparsers(dest='command', help="Sub-commands")
    serve_parser = sub_parsers.add_parser("serve", help="Serve via HTTP.")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8000)
    return parser.parse_args(args)


def main():
    args = parse_config(sys.argv[1:])
    if args.version:
        from . import __version__
        print(f'servecmd {__version__}')
    conf.CONFIG.no_clean = args.no_clean
    conf.CONFIG.verbosity = args.verbose
    if args.config:
        conf.load(args.config)
    if args.command == "serve":
        cmd_manager.load_cmd_configs()
        uvicorn.run("servecmd.server:app", host=args.host, port=args.port)


if __name__ == "__main__":
    main()
