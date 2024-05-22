import sys
import argparse
import uvicorn
from . import conf
from . import cmd_manager


def parse_config(args):
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="", help="Config file.")
    sub_parsers = parser.add_subparsers(dest='command', help="Sub-commands")
    serve_parser = sub_parsers.add_parser("serve", help="Serve via HTTP.")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8000)
    return parser.parse_args(args)


def main():
    args = parse_config(sys.argv[1:])
    if args.config:
        conf.load(args.config)
    if args.command == "serve":
        cmd_manager.load_cmd_configs()
        uvicorn.run("servecmd.server:app", host=args.host, port=args.port)


if __name__ == "__main__":
    main()
