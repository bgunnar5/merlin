import os
import sys
import logging

import click

from merlin.cli.utils import setup_logging


plugin_folder = os.path.join(os.path.dirname(__file__), "commands")
LOG = logging.getLogger("merlin")


class MyCLI(click.MultiCommand):
    def list_commands(self, ctx):
        rv = []
        for filename in os.listdir(plugin_folder):
            if filename.startswith("__"):
                continue
            if filename.endswith(".py"):
                rv.append(filename[:-3])
        rv.sort()
        return rv

    def get_command(self, ctx, name):
        ns = {}
        fn = os.path.join(plugin_folder, name + ".py")
        with open(fn) as f:
            code = compile(f.read(), fn, "exec")
            eval(code, ns, ns)
        return ns["cli"]

def main():
    setup_logging(logger=LOG, log_level="INFO", colors=True) #TODO level
    cli = MyCLI(help="Merlin!")  # TODO add --level, --version
    cli()

if __name__ == "__main__":
    sys.exit(main())
