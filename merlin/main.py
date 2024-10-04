"""The top level main function for invoking Merlin."""

###############################################################################
# Copyright (c) 2023, Lawrence Livermore National Security, LLC.
# Produced at the Lawrence Livermore National Laboratory
# Written by the Merlin dev team, listed in the CONTRIBUTORS file.
# <merlin@llnl.gov>
#
# LLNL-CODE-797170
# All rights reserved.
# This file is part of Merlin, Version: 1.12.2b1.
#
# For details, see https://github.com/LLNL/merlin.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
###############################################################################

from __future__ import print_function

import glob
import logging
import os
import sys
import time
import traceback
from argparse import (
    ArgumentDefaultsHelpFormatter,
    ArgumentParser,
    Namespace,
    RawDescriptionHelpFormatter,
    RawTextHelpFormatter,
)
from contextlib import suppress
from typing import Dict, List, Optional, Tuple, Union

from tabulate import tabulate

from merlin import VERSION, router
from merlin.ascii_art import banner_small
from merlin.examples.generator import list_examples, setup_example
from merlin.log_formatter import setup_logging
from merlin.server.server_commands import config_server, init_server, restart_server, start_server, status_server, stop_server
from merlin.spec.expansion import RESERVED, get_spec_with_expansion
from merlin.spec.specification import MerlinSpec
from merlin.study.status import DetailedStatus, Status
from merlin.study.status_constants import VALID_RETURN_CODES, VALID_STATUS_FILTERS
from merlin.study.status_renderers import status_renderer_factory
from merlin.study.study import MerlinStudy
from merlin.utils import ARRAY_FILE_FORMATS, verify_dirpath, verify_filepath


LOG = logging.getLogger("merlin")
DEFAULT_LOG_LEVEL = "INFO"


class HelpParser(ArgumentParser):
    """This class overrides the error message of the argument parser to
    print the help message when an error happens."""

    def error(self, message: str):
        """
        Override the error message of the ArgumentParser class.

        Args:
            message: The error message to log.
        """
        sys.stderr.write(f"error: {message}\n")
        self.print_help()
        sys.exit(2)


def parse_override_vars(
    variables_list: Optional[List[str]],
) -> Optional[Dict[str, Union[str, int]]]:
    """
    Parse a list of command-line variables into a dictionary of key-value pairs.

    This function takes an optional list of strings following the syntax 
    "KEY=val" and converts them into a dictionary. It validates the format 
    of the variables and ensures that keys are valid according to specified rules.

    Args:
        variables_list: An optional list of strings, where each string should be in the 
            format "KEY=val", e.g., ["KEY1=value1", "KEY2=42"].

    Returns: 
        A dictionary where the keys are variable names (str) and the 
            values are either strings or integers. If `variables_list` is 
            None or empty, returns None.
    
    Raises:
        ValueError: If the input format is incorrect, including:\n
            - Missing '=' operator.
            - Excess '=' operators in a variable assignment.
            - Invalid variable names (must be alphanumeric and underscores).
            - Attempting to override reserved variable names.
    """
    if variables_list is None:
        return None
    LOG.debug(f"Command line override variables = {variables_list}")
    result: Dict[str, Union[str, int]] = {}
    arg: str
    for arg in variables_list:
        try:
            if "=" not in arg:
                raise ValueError("--vars requires '=' operator. See 'merlin run --help' for an example.")
            entry: str = arg.split("=")
            if len(entry) != 2:
                raise ValueError("--vars requires ONE '=' operator (without spaces) per variable assignment.")
            key: str = entry[0]
            if key is None or key == "" or "$" in key:
                raise ValueError("--vars requires valid variable names comprised of alphanumeric characters and underscores.")
            if key in RESERVED:
                raise ValueError(f"Cannot override reserved word '{key}'! Reserved words are: {RESERVED}.")

            val: Union[str, int] = entry[1]
            with suppress(ValueError):
                int(val)
                val = int(val)
            result[key] = val

        except Exception as excpt:
            raise ValueError(
                f"{excpt} Bad '--vars' formatting on command line. See 'merlin run --help' for an example."
            ) from excpt
    return result


def get_merlin_spec_with_override(args: Namespace) -> Tuple[MerlinSpec, str]:
    """
    Shared command to retrieve a `MerlinSpec` object and an expanded filepath.

    This function processes parsed command-line interface (CLI) arguments to validate 
    and expand the specified filepath and any associated variables. It then constructs 
    and returns a `MerlinSpec` object based on the provided specification. 

    Args:
        args: Parsed CLI arguments containing:\n
            - `specification`: the path to the specification file
            - `variables`: optional variable overrides to customize the spec.

    Returns:
        spec: An instance of the `MerlinSpec` class with the 
              expanded configuration based on the provided filepath and variables.
        filepath: The expanded filepath derived from the specification.
    """
    filepath = verify_filepath(args.specification)
    variables_dict = parse_override_vars(args.variables)
    spec = get_spec_with_expansion(filepath, override_vars=variables_dict)
    return spec, filepath


def process_run(args: Namespace):
    """
    CLI command for running a study.

    This function initializes and runs a study using the specified parameters.
    It handles file verification, variable parsing, and checks for required 
    arguments related to the study configuration and execution.

    Args:
        args: Parsed CLI arguments containing:\n
            - `specification`: Path to the specification file for the study.
            - `variables`: Optional variable overrides for the study.
            - `samples_file`: Optional path to a samples file.
            - `dry`: If True, runs the study in dry-run mode (without actual execution).
            - `no_errors`: If True, suppresses error reporting.
            - `pgen_file`: Optional path to the pgen file, required if `pargs` is specified.
            - `pargs`: Additional arguments for parallel processing.

    Raises:
        ValueError: 
            If the `pargs` parameter is used without specifying a `pgen_file`.
    """
    print(banner_small)
    filepath: str = verify_filepath(args.specification)
    variables_dict: str = parse_override_vars(args.variables)
    samples_file: Optional[str] = None
    if args.samples_file:
        samples_file = verify_filepath(args.samples_file)

    # pgen checks
    if args.pargs and not args.pgen_file:
        raise ValueError("Cannot use the 'pargs' parameter without specifying a 'pgen'!")
    if args.pgen_file:
        verify_filepath(args.pgen_file)

    study: MerlinStudy = MerlinStudy(
        filepath,
        override_vars=variables_dict,
        samples_file=samples_file,
        dry_run=args.dry,
        no_errors=args.no_errors,
        pgen_file=args.pgen_file,
        pargs=args.pargs,
    )
    router.run_task_server(study, args.run_mode)


def process_restart(args: Namespace):
    """
    CLI command for restarting a study.

    This function handles the restart process by verifying the specified restart 
    directory, locating a valid provenance specification file, and initiating 
    the study from that point.

    Args:
        args: Parsed CLI arguments containing:\n
            - `restart_dir`: Path to the directory where the restart specifications are located.
            - `run_mode`: The mode for running the study (e.g., normal, dry-run).

    Raises:
        ValueError: If the `restart_dir` does not contain a valid provenance spec file or 
            if multiple files match the specified pattern.
    """
    print(banner_small)
    restart_dir: str = verify_dirpath(args.restart_dir)
    filepath: str = os.path.join(args.restart_dir, "merlin_info", "*.expanded.yaml")
    possible_specs: Optional[List[str]] = glob.glob(filepath)
    if not possible_specs:  # len == 0
        raise ValueError(f"'{filepath}' does not match any provenance spec file to restart from.")
    if len(possible_specs) > 1:
        raise ValueError(f"'{filepath}' matches more than one provenance spec file to restart from.")
    filepath: str = verify_filepath(possible_specs[0])
    LOG.info(f"Restarting workflow at '{restart_dir}'")
    study: MerlinStudy = MerlinStudy(filepath, restart_dir=restart_dir)
    router.run_task_server(study, args.run_mode)


def launch_workers(args: Namespace):
    """
    CLI command for launching workers.

    This function initializes worker processes for executing tasks as defined
    in the Merlin specification.

    Args:
        args: Parsed CLI arguments containing:\n
            - `worker_echo_only`: If True, don't start the workers and just echo the launch command
            - Additional worker-related parameters such as:
                - `worker_steps`: Only start workers for these steps.
                - `worker_args`: Arguments to pass to the worker processes.
                - `disable_logs`: If True, disables logging for the worker processes.
    """
    if not args.worker_echo_only:
        print(banner_small)
    spec, filepath = get_merlin_spec_with_override(args)
    if not args.worker_echo_only:
        LOG.info(f"Launching workers from '{filepath}'")
    launch_worker_status = router.launch_workers(
        spec, args.worker_steps, args.worker_args, args.disable_logs, args.worker_echo_only
    )
    if args.worker_echo_only:
        print(launch_worker_status)
    else:
        LOG.debug(f"celery command: {launch_worker_status}")


def purge_tasks(args: Namespace):
    """
    CLI command for purging tasks from the task server.

    This function removes specified tasks from the task server based on the provided
    Merlin specification. It allows for targeted purging or forced removal of tasks.

    Args:
        args: Parsed CLI arguments containing:\n
            - `purge_force`: If True, forces the purge operation without confirmation.
            - `purge_steps`: Steps or criteria based on which tasks will be purged.
    """
    print(banner_small)
    spec, _ = get_merlin_spec_with_override(args)
    ret = router.purge_tasks(
        spec.merlin["resources"]["task_server"],
        spec,
        args.purge_force,
        args.purge_steps,
    )

    LOG.info(f"Purge return = {ret} .")


def query_status(args: Namespace):
    """
    CLI command for querying the status of studies.

    This function processes the given command-line arguments to determine the 
    status of a study. It constructs either a `Status` object or a `DetailedStatus` 
    object based on the specified command and the arguments provided. The function 
    handles validations for the task server input and the output format specified 
    for status dumping.

    Object mapping:
        - `merlin status` -> `Status` object
        - `merlin detailed-status` -> `DetailedStatus` object

    Args:
        args: Parsed CLI arguments containing user inputs for the status query.

    Raises:
        ValueError: 
            If the task server specified is not supported (only "celery" is valid).
            If the --dump filename provided does not end with ".csv" or ".json".
    """
    print(banner_small)

    # Ensure task server is valid
    if args.task_server != "celery":
        raise ValueError("Currently the only supported task server is celery.")

    # Make sure dump is valid if provided
    if args.dump and (not args.dump.endswith(".csv") and not args.dump.endswith(".json")):
        raise ValueError("The --dump option takes a filename that must end with .csv or .json")

    # Establish whether the argument provided by the user was a spec file or a study directory
    spec_display = False
    try:
        file_or_ws = verify_filepath(args.spec_or_workspace)
        spec_display = True
    except ValueError:
        try:
            file_or_ws = verify_dirpath(args.spec_or_workspace)
        except ValueError:
            LOG.error(f"The file or directory path {args.spec_or_workspace} does not exist.")
            return None

    # If we're loading status based on a spec, load in the spec provided
    if spec_display:
        args.specification = file_or_ws
        args.spec_provided = get_spec_with_expansion(args.specification)

    # Get either a Status object or DetailedStatus object
    if args.detailed:
        status_obj = DetailedStatus(args, spec_display, file_or_ws)
    else:
        status_obj = Status(args, spec_display, file_or_ws)

    # Handle output appropriately
    if args.dump:
        status_obj.dump()
    else:
        status_obj.display()

    return None


def query_queues(args: Namespace):
    """
    CLI command for finding all workers and their associated queues.

    This function processes the command-line arguments to retrieve and display 
    information about the available workers and their queues within the task server. 
    It validates the necessary parameters, handles potential file dumping, and 
    formats the output for easy readability.

    Args:
        args: Parsed CLI arguments containing user inputs related to the query.

    Raises:
        ValueError: 
            If a specification is not provided when steps are specified and the 
            steps do not include "all".
            If variables are included without a corresponding specification.
            If the specified dump filename does not end with '.json' or '.csv'.
    """
    print(banner_small)

    # Ensure a spec is provided if steps are provided
    if not args.specification:
        if "all" not in args.steps:
            raise ValueError("The --steps argument MUST be used with the --specification argument.")
        if args.variables:
            raise ValueError("The --vars argument MUST be used with the --specification argument.")

    # Ensure a supported file type is provided with the dump option
    if args.dump is not None:
        if not args.dump.endswith(".json") and not args.dump.endswith(".csv"):
            raise ValueError("Unsupported file type. Dump files must be either '.json' or '.csv'.")

    spec = None
    # Load the spec if necessary
    if args.specification:
        spec, _ = get_merlin_spec_with_override(args)

    # Obtain the queue information
    queue_information = router.query_queues(args.task_server, spec, args.steps, args.specific_queues)

    if queue_information:
        # Format the queue information so we can pass it to the tabulate library
        formatted_queue_info = [("Queue Name", "Task Count", "Worker Count")]
        for queue_name, queue_stats in queue_information.items():
            formatted_queue_info.append((queue_name, queue_stats["jobs"], queue_stats["consumers"]))

        # Print the queue information
        print()
        print(tabulate(formatted_queue_info, headers="firstrow"))
        print()

        # Dump queue information to an output file if necessary
        if args.dump:
            router.dump_queue_info(args.task_server, queue_information, args.dump)


def query_workers(args: Namespace):
    """
    CLI command for finding all workers.

    This function retrieves and queries the names of any active workers. 
    If the `--spec` argument is included, only query the workers defined in the spec file.

    Args:
        args: Parsed command-line arguments, which may include:\n
            - `spec`: Path to the specification file.
            - `task_server`: Address of the task server to query.
            - `queues`: List of queue names to filter workers.
            - `workers`: List of specific worker names to query.
    """
    print(banner_small)

    # Get the workers from the spec file if --spec provided
    worker_names = []
    if args.spec:
        spec_path = verify_filepath(args.spec)
        spec = MerlinSpec.load_specification(spec_path)
        worker_names = spec.get_worker_names()
        for worker_name in worker_names:
            if "$" in worker_name:
                LOG.warning(f"Worker '{worker_name}' is unexpanded. Target provenance spec instead?")
        LOG.debug(f"Searching for the following workers to stop based on the spec {args.spec}: {worker_names}")

    router.query_workers(args.task_server, worker_names, args.queues, args.workers)


def stop_workers(args: Namespace):
    """
    CLI command for stopping all workers.

    This function stops any active workers connected to a user's task server.
    If the `--spec` argument is provided, this function retrieves the names of
    workers from a the spec file and then issues a command to stop them.

    Args:
        args: Parsed command-line arguments, which may include:\n
            - `spec`: Path to the specification file to load worker names.
            - `task_server`: Address of the task server to send the stop command to.
            - `queues`: List of queue names to filter the workers.
            - `workers`: List of specific worker names to stop.
    """
    print(banner_small)
    worker_names = []

    # Load in the spec if one was provided via the CLI
    if args.spec:
        spec_path = verify_filepath(args.spec)
        spec = MerlinSpec.load_specification(spec_path)
        worker_names = spec.get_worker_names()
        for worker_name in worker_names:
            if "$" in worker_name:
                LOG.warning(f"Worker '{worker_name}' is unexpanded. Target provenance spec instead?")

    # Send stop command to router
    router.stop_workers(args.task_server, worker_names, args.queues, args.workers)


def print_info(args: Namespace):
    """
    CLI command to print merlin configuration info.

    Args:
        args: Parsed CLI arguments.
    """
    # if this is moved to the toplevel per standard style, merlin is unable to generate the (needed) default config file
    from merlin import display  # pylint: disable=import-outside-toplevel

    display.print_info(args)


def config_merlin(args: Namespace) -> None:
    """
    CLI command to set up the default Merlin configuration.

    This function initializes the configuration app.yaml file that's
    necessary to connect Merlin to a central server. If the output
    directory is not specified via the command-line arguments, it
    defaults to the user's home directory under `.merlin`.

    Args:
        args: Parsed command-line arguments, which may include:\n
            - `output_dir`: Path to the output directory for 
              configuration files. If not provided, defaults to 
              `~/.merlin`.
            - `task_server`: Address of the task server for the 
              configuration.
            - `broker`: Address of the broker service to use.
            - `test`: Flag indicating whether to run in test mode.
    """
    output_dir: Optional[str] = args.output_dir
    if output_dir is None:
        user_home: str = os.path.expanduser("~")
        output_dir: str = os.path.join(user_home, ".merlin")

    router.create_config(args.task_server, output_dir, args.broker, args.test)


def process_example(args: Namespace) -> None:
    """
    CLI command to set up or list Merlin example workflows.

    This function either lists all available example workflows or sets 
    up a specified example workflow to be run in the root directory. The 
    behavior is determined by the `workflow` argument.

    Args:
        args: Parsed command-line arguments, which may include:\n
            - `workflow`: The action to perform; should be "list" 
              to display all examples or the name of a specific example 
              workflow to set up.
            - `path`: The directory where the example workflow 
              should be set up. Only applicable when `workflow` is not "list".
    """
    if args.workflow == "list":
        print(list_examples())
    else:
        print(banner_small)
        setup_example(args.workflow, args.path)


def process_monitor(args: Namespace):
    """
    CLI command to monitor Merlin workers and queues to maintain 
    allocation status.

    This function periodically checks the status of Merlin workers and 
    the associated queues to ensure that the allocation remains active. 
    It includes a sleep interval to wait before each check, including
    the initial one.

    Args:
        args: Parsed command-line arguments, which may include:\n
            - `sleep`: The duration (in seconds) to wait before 
              checking the queue status again.
    """
    LOG.info("Monitor: checking queues ...")
    spec, _ = get_merlin_spec_with_override(args)

    # Give the user time to queue up jobs in case they haven't already
    time.sleep(args.sleep)

    # Check if we still need our allocation
    while router.check_merlin_status(args, spec):
        LOG.info("Monitor: found tasks in queues and/or tasks being processed")
        time.sleep(args.sleep)
    LOG.info("Monitor: ... stop condition met")


def process_server(args: Namespace):
    """
    Route to the appropriate server function based on the command 
    specified via the CLI.

    This function processes commands related to server management, 
    directing the flow to the corresponding function for actions such 
    as initializing, starting, stopping, checking status, restarting, 
    or configuring the server.

    Args:
        args: Parsed command-line arguments, which includes:\n
            - `commands`: The server management command to execute. 
              Possible values are:
                - "init": Initialize the server.
                - "start": Start the server.
                - "stop": Stop the server.
                - "status": Check the server status.
                - "restart": Restart the server.
                - "config": Configure the server.
    """
    if args.commands == "init":
        init_server()
    elif args.commands == "start":
        start_server()
    elif args.commands == "stop":
        stop_server()
    elif args.commands == "status":
        status_server()
    elif args.commands == "restart":
        restart_server()
    elif args.commands == "config":
        config_server(args)


# Pylint complains that there's too many statements here and wants us
# to split the function up but that wouldn't make much sense so we ignore it
def setup_argparse() -> None:  # pylint: disable=R0915
    """
    Set up the command-line argument parser for the Merlin package.

    This function configures the ArgumentParser for the Merlin CLI, allowing users
    to interact with various commands related to workflow management and task handling.
    It includes options for running a workflow, restarting tasks, purging task queues,
    generating configuration files, and managing/configuring the server.
    """
    parser: HelpParser = HelpParser(
        prog="merlin",
        description=banner_small,
        formatter_class=RawDescriptionHelpFormatter,
        epilog="See merlin <command> --help for more info",
    )
    parser.add_argument("-v", "--version", action="version", version=VERSION)
    subparsers: ArgumentParser = parser.add_subparsers(dest="subparsers")
    subparsers.required = True

    # merlin --level
    parser.add_argument(
        "-lvl",
        "--level",
        action="store",
        dest="level",
        type=str,
        default=DEFAULT_LOG_LEVEL,
        help="Set the log level. Options: DEBUG, INFO, WARNING, ERROR. [Default: %(default)s]",
    )

    # merlin run
    run: ArgumentParser = subparsers.add_parser(
        "run",
        help="Run a workflow using a Merlin or Maestro YAML study " "specification.",
        formatter_class=ArgumentDefaultsHelpFormatter,
    )
    run.set_defaults(func=process_run)
    run.add_argument("specification", type=str, help="Path to a Merlin or Maestro YAML file")
    run.add_argument(
        "--local",
        action="store_const",
        dest="run_mode",
        const="local",
        default="distributed",
        help="Run locally instead of distributed",
    )
    run.add_argument(
        "--vars",
        action="store",
        dest="variables",
        type=str,
        nargs="+",
        default=None,
        help="Specify desired Merlin variable values to override those found in the specification. Space-delimited. "
        "Example: '--vars LEARN=path/to/new_learn.py EPOCHS=3'",
    )
    # TODO add all supported formats to doc string  # pylint: disable=fixme
    run.add_argument(
        "--samplesfile",
        action="store",
        dest="samples_file",
        type=str,
        default=None,
        help=f"Specify file containing samples. Valid choices: {ARRAY_FILE_FORMATS}",
    )
    run.add_argument(
        "--dry",
        action="store_true",
        dest="dry",
        default=False,
        help="Flag to dry-run a workflow, which sets up the workspace but does not launch tasks.",
    )
    run.add_argument(
        "--no-errors",
        action="store_true",
        dest="no_errors",
        default=False,
        help="Flag to ignore some flux errors for testing (often used with --dry --local).",
    )
    run.add_argument(
        "--pgen",
        action="store",
        dest="pgen_file",
        type=str,
        default=None,
        help="Provide a pgen file to override global.parameters.",
    )
    run.add_argument(
        "--pargs",
        type=str,
        action="append",
        default=[],
        help="A string that represents a single argument to pass "
        "a custom parameter generation function. Reuse '--parg' "
        "to pass multiple arguments. [Use with '--pgen']",
    )

    # merlin restart
    restart: ArgumentParser = subparsers.add_parser(
        "restart",
        help="Restart a workflow using an existing Merlin workspace.",
        formatter_class=ArgumentDefaultsHelpFormatter,
    )
    restart.set_defaults(func=process_restart)
    restart.add_argument("restart_dir", type=str, help="Path to an existing Merlin workspace directory")
    restart.add_argument(  # TODO should this just be boolean instead of store_const?
        "--local",
        action="store_const",
        dest="run_mode",
        const="local",
        default="distributed",
        help="Run locally instead of distributed",
    )

    # merlin purge
    purge: ArgumentParser = subparsers.add_parser(
        "purge",
        help="Remove all tasks from all merlin queues (default).              "
        "If a user would like to purge only selected queues use:    "
        "--steps to give a steplist, the queues will be defined from the step list",
        formatter_class=ArgumentDefaultsHelpFormatter,
    )
    purge.set_defaults(func=purge_tasks)
    purge.add_argument("specification", type=str, help="Path to a Merlin YAML spec file")
    purge.add_argument(
        "-f",
        "--force",
        action="store_true",
        dest="purge_force",
        default=False,
        help="Purge the tasks without confirmation",
    )
    purge.add_argument(
        "--steps",
        nargs="+",
        type=str,
        dest="purge_steps",
        default=["all"],
        help="The specific steps in the YAML file from which you want to purge the queues. \
        The input is a space separated list.",
    )
    purge.add_argument(
        "--vars",
        action="store",
        dest="variables",
        type=str,
        nargs="+",
        default=None,
        help="Specify desired Merlin variable values to override those found in the specification. Space-delimited. "
        "Example: '--vars MY_QUEUE=hello'",
    )

    mconfig: ArgumentParser = subparsers.add_parser(
        "config",
        help="Create a default merlin server config file in ~/.merlin",
        formatter_class=ArgumentDefaultsHelpFormatter,
    )
    mconfig.set_defaults(func=config_merlin)
    mconfig.add_argument(
        "--task_server",
        type=str,
        default="celery",
        help="Task server type for which to create the config.\
                            Default: %(default)s",
    )
    mconfig.add_argument(
        "-o",
        "--output_dir",
        type=str,
        default=None,
        help="Optional directory to place the default config file.\
                            Default: ~/.merlin",
    )
    mconfig.add_argument(
        "--broker",
        type=str,
        default=None,
        help="Optional broker type, backend will be redis\
                            Default: rabbitmq",
    )
    mconfig.add_argument(
        "--test",
        type=str,
        default=None,
        help="A config used in the testing suite (or for exemplative purposes).\
                            Default: rabbitmq",
    )

    # merlin example
    example: ArgumentParser = subparsers.add_parser(
        "example",
        help="Generate an example merlin workflow.",
        formatter_class=RawTextHelpFormatter,
    )
    example.add_argument(
        "workflow",
        action="store",
        type=str,
        help="The name of the example workflow to setup. Use 'merlin example list' to see available options.",
    )
    example.add_argument(
        "-p",
        "--path",
        action="store",
        type=str,
        default=None,
        help="Specify a path to write the workflow to. Defaults to current working directory",
    )
    example.set_defaults(func=process_example)

    generate_worker_touching_parsers(subparsers)

    generate_diagnostic_parsers(subparsers)

    # merlin server
    server: ArgumentParser = subparsers.add_parser(
        "server",
        help="Manage broker and results server for merlin workflow.",
        formatter_class=ArgumentDefaultsHelpFormatter,
    )
    server.set_defaults(func=process_server)

    server_commands: ArgumentParser = server.add_subparsers(dest="commands")

    server_init: ArgumentParser = server_commands.add_parser(
        "init",
        help="Initialize merlin server resources.",
        description="Initialize merlin server",
        formatter_class=ArgumentDefaultsHelpFormatter,
    )
    server_init.set_defaults(func=process_server)

    server_status: ArgumentParser = server_commands.add_parser(
        "status",
        help="View status of the current server containers.",
        description="View status",
        formatter_class=ArgumentDefaultsHelpFormatter,
    )
    server_status.set_defaults(func=process_server)

    server_start: ArgumentParser = server_commands.add_parser(
        "start",
        help="Start a containerized server to be used as an broker and results server.",
        description="Start server",
        formatter_class=ArgumentDefaultsHelpFormatter,
    )
    server_start.set_defaults(func=process_server)

    server_stop: ArgumentParser = server_commands.add_parser(
        "stop",
        help="Stop an instance of redis containers currently running.",
        description="Stop server.",
        formatter_class=ArgumentDefaultsHelpFormatter,
    )
    server_stop.set_defaults(func=process_server)

    server_stop: ArgumentParser = server_commands.add_parser(
        "restart",
        help="Restart merlin server instance",
        description="Restart server.",
        formatter_class=ArgumentDefaultsHelpFormatter,
    )
    server_stop.set_defaults(func=process_server)

    server_config: ArgumentParser = server_commands.add_parser(
        "config",
        help="Making configurations for to the merlin server instance.",
        description="Config server.",
        formatter_class=ArgumentDefaultsHelpFormatter,
    )
    server_config.add_argument(
        "-ip",
        "--ipaddress",
        action="store",
        type=str,
        # default="127.0.0.1",
        help="Set the binded IP address for the merlin server container.",
    )
    server_config.add_argument(
        "-p",
        "--port",
        action="store",
        type=int,
        # default=6379,
        help="Set the binded port for the merlin server container.",
    )
    server_config.add_argument(
        "-pwd",
        "--password",
        action="store",
        type=str,
        # default="~/.merlin/redis.pass",
        help="Set the password file to be used for merlin server container.",
    )
    server_config.add_argument(
        "--add-user",
        action="store",
        nargs=2,
        type=str,
        help="Create a new user for merlin server instance. (Provide both username and password)",
    )
    server_config.add_argument("--remove-user", action="store", type=str, help="Remove an exisiting user.")
    server_config.add_argument(
        "-d",
        "--directory",
        action="store",
        type=str,
        # default="./",
        help="Set the working directory of the merlin server container.",
    )
    server_config.add_argument(
        "-ss",
        "--snapshot-seconds",
        action="store",
        type=int,
        # default=300,
        help="Set the number of seconds merlin server waits before checking if a snapshot is needed.",
    )
    server_config.add_argument(
        "-sc",
        "--snapshot-changes",
        action="store",
        type=int,
        # default=100,
        help="Set the number of changes that are required to be made to the merlin server before a snapshot is made.",
    )
    server_config.add_argument(
        "-sf",
        "--snapshot-file",
        action="store",
        type=str,
        # default="dump.db",
        help="Set the snapshot filename for database dumps.",
    )
    server_config.add_argument(
        "-am",
        "--append-mode",
        action="store",
        type=str,
        # default="everysec",
        help="The appendonly mode to be set. The avaiable options are always, everysec, no.",
    )
    server_config.add_argument(
        "-af",
        "--append-file",
        action="store",
        type=str,
        # default="appendonly.aof",
        help="Set append only filename for merlin server container.",
    )

    return parser


def generate_worker_touching_parsers(subparsers: ArgumentParser) -> None:
    """
    Generate command-line argument parsers for managing worker operations.

    This function sets up subparsers for CLI commands that directly control or invoke 
    workers in the context of the Merlin framework. It provides options for running,
    querying, stopping, and monitoring workers associated with a Merlin YAML study 
    specification.

    Args:
        subparsers: An instance of ArgumentParser for adding command-line subcommands related 
            to worker management.
    """
    # merlin run-workers
    run_workers: ArgumentParser = subparsers.add_parser(
        "run-workers",
        help="Run the workers associated with the Merlin YAML study "
        "specification. Does -not- queue tasks, just workers tied "
        "to the correct queues.",
        formatter_class=ArgumentDefaultsHelpFormatter,
    )
    run_workers.set_defaults(func=launch_workers)
    run_workers.add_argument("specification", type=str, help="Path to a Merlin YAML spec file")
    run_workers.add_argument(
        "--worker-args",
        type=str,
        dest="worker_args",
        default="",
        help="celery worker arguments in quotes.",
    )
    run_workers.add_argument(
        "--steps",
        nargs="+",
        type=str,
        dest="worker_steps",
        default=["all"],
        help="The specific steps in the YAML file you want workers for",
    )
    run_workers.add_argument(
        "--echo",
        action="store_true",
        default=False,
        dest="worker_echo_only",
        help="Just echo the command; do not actually run it",
    )
    run_workers.add_argument(
        "--vars",
        action="store",
        dest="variables",
        type=str,
        nargs="+",
        default=None,
        help="Specify desired Merlin variable values to override those found in the specification. Space-delimited. "
        "Example: '--vars LEARN=path/to/new_learn.py EPOCHS=3'",
    )
    run_workers.add_argument(
        "--disable-logs",
        action="store_true",
        help="Turn off the logs for the celery workers. Note: having the -l flag "
        "in your workers' args section will overwrite this flag for that worker.",
    )

    # merlin query-workers
    query: ArgumentParser = subparsers.add_parser("query-workers", help="List connected task server workers.")
    query.set_defaults(func=query_workers)
    query.add_argument(
        "--task_server",
        type=str,
        default="celery",
        help="Task server type from which to query workers.\
                            Default: %(default)s",
    )
    query.add_argument(
        "--spec",
        type=str,
        default=None,
        help="Path to a Merlin YAML spec file from which to read worker names to query.",
    )
    query.add_argument("--queues", type=str, default=None, nargs="+", help="Specific queues to query workers from.")
    query.add_argument(
        "--workers",
        type=str,
        action="store",
        nargs="+",
        default=None,
        help="Regex match for specific workers to query.",
    )

    # merlin stop-workers
    stop: ArgumentParser = subparsers.add_parser("stop-workers", help="Attempt to stop all task server workers.")
    stop.set_defaults(func=stop_workers)
    stop.add_argument(
        "--spec",
        type=str,
        default=None,
        help="Path to a Merlin YAML spec file from which to read worker names to stop.",
    )
    stop.add_argument(
        "--task_server",
        type=str,
        default="celery",
        help="Task server type from which to stop workers.\
                            Default: %(default)s",
    )
    stop.add_argument("--queues", type=str, default=None, nargs="+", help="specific queues to stop")
    stop.add_argument(
        "--workers",
        type=str,
        action="store",
        nargs="+",
        default=None,
        help="regex match for specific workers to stop",
    )

    # merlin monitor
    monitor: ArgumentParser = subparsers.add_parser(
        "monitor",
        help="Check for active workers on an allocation.",
        formatter_class=RawTextHelpFormatter,
    )
    monitor.add_argument("specification", type=str, help="Path to a Merlin YAML spec file")
    monitor.add_argument(
        "--steps",
        nargs="+",
        type=str,
        dest="steps",
        default=["all"],
        help="The specific steps (tasks on the server) in the YAML file defining the queues you want to monitor",
    )
    monitor.add_argument(
        "--vars",
        action="store",
        dest="variables",
        type=str,
        nargs="+",
        default=None,
        help="Specify desired Merlin variable values to override those found in the specification. Space-delimited. "
        "Example: '--vars LEARN=path/to/new_learn.py EPOCHS=3'",
    )
    monitor.add_argument(
        "--task_server",
        type=str,
        default="celery",
        help="Task server type for which to monitor the workers.\
                              Default: %(default)s",
    )
    monitor.add_argument(
        "--sleep",
        type=int,
        default=60,
        help="Sleep duration between checking for workers.\
                                    Default: %(default)s",
    )
    monitor.set_defaults(func=process_monitor)


def generate_diagnostic_parsers(subparsers: ArgumentParser):
    """
    Generate command-line argument parsers for diagnostic operations in the Merlin framework.

    This function sets up subparsers for CLI commands that handle diagnostics related
    to Merlin jobs. It provides options to check the status of studies, gather queue 
    statistics, and retrieve configuration information, making it easier for users to 
    diagnose issues with their workflows.

    Args:
        subparsers: An instance of ArgumentParser that will be used to add command-line 
            subcommands for various diagnostic activities.
    """
    # merlin status
    status_cmd: ArgumentParser = subparsers.add_parser(
        "status",
        help="Display a summary of the status of a study.",
    )
    status_cmd.set_defaults(func=query_status, detailed=False)
    status_cmd.add_argument("spec_or_workspace", type=str, help="Path to a Merlin YAML spec file or a launched Merlin study")
    status_cmd.add_argument(
        "--cb-help", action="store_true", help="Colorblind help; uses different symbols to represent different statuses"
    )
    status_cmd.add_argument(
        "--dump", type=str, help="Dump the status to a file. Provide the filename (must be .csv or .json).", default=None
    )
    status_cmd.add_argument(
        "--no-prompts",
        action="store_true",
        help="Ignore any prompts provided. This will default to the latest study \
            if you provide a spec file rather than a study workspace.",
    )
    status_cmd.add_argument(
        "--task_server",
        type=str,
        default="celery",
        help="Task server type.\
                            Default: %(default)s",
    )
    status_cmd.add_argument(
        "-o",
        "--output-path",
        action="store",
        type=str,
        default=None,
        help="Specify a location to look for output workspaces. Only used when a spec file is passed as the argument "
        "to 'status'; this will NOT be used if an output workspace is passed as the argument.",
    )

    # merlin detailed-status
    detailed_status: ArgumentParser = subparsers.add_parser(
        "detailed-status",
        help="Display a task-by-task status of a study.",
    )
    detailed_status.set_defaults(func=query_status, detailed=True)
    detailed_status.add_argument(
        "spec_or_workspace", type=str, help="Path to a Merlin YAML spec file or a launched Merlin study"
    )
    detailed_status.add_argument(
        "--dump", type=str, help="Dump the status to a file. Provide the filename (must be .csv or .json).", default=None
    )
    detailed_status.add_argument(
        "--task_server",
        type=str,
        default="celery",
        help="Task server type.\
                            Default: %(default)s",
    )
    detailed_status.add_argument(
        "-o",
        "--output-path",
        action="store",
        type=str,
        default=None,
        help="Specify a location to look for output workspaces. Only used when a spec file is passed as the argument "
        "to 'status'; this will NOT be used if an output workspace is passed as the argument.",
    )
    status_filter_group = detailed_status.add_argument_group("filter options")
    status_filter_group.add_argument(
        "--max-tasks", action="store", type=int, help="Sets a limit on how many tasks can be displayed"
    )
    status_filter_group.add_argument(
        "--return-code",
        action="store",
        nargs="+",
        type=str,
        choices=VALID_RETURN_CODES,
        help="Filter which tasks to display based on their return code",
    )
    status_filter_group.add_argument(
        "--steps",
        nargs="+",
        type=str,
        dest="steps",
        default=["all"],
        help="Filter which tasks to display based on the steps they're associated with",
    )
    status_filter_group.add_argument(
        "--task-queues",
        nargs="+",
        type=str,
        help="Filter which tasks to display based on the task queue they're in",
    )
    status_filter_group.add_argument(
        "--task-status",
        action="store",
        nargs="+",
        type=str,
        choices=VALID_STATUS_FILTERS,
        help="Filter which tasks to display based on their status",
    )
    status_filter_group.add_argument(
        "--workers",
        nargs="+",
        type=str,
        help="Filter which tasks to display based on which workers are processing them",
    )
    status_display_group = detailed_status.add_argument_group("display options")
    status_display_group.add_argument(
        "--disable-pager", action="store_true", help="Turn off the pager functionality when viewing the status"
    )
    status_display_group.add_argument(
        "--disable-theme",
        action="store_true",
        help="Turn off styling for the status layout (If you want styling but it's not working, try modifying "
        "the MANPAGER or PAGER environment variables to be 'less -r'; i.e. export MANPAGER='less -r')",
    )
    status_display_group.add_argument(
        "--layout",
        type=str,
        choices=status_renderer_factory.get_layouts(),
        default="default",
        help="Alternate status layouts [Default: %(default)s]",
    )
    status_display_group.add_argument(
        "--no-prompts",
        action="store_true",
        help="Ignore any prompts provided. This will default to the latest study \
            if you provide a spec file rather than a study workspace.",
    )

    # merlin queue-info
    queue_info: ArgumentParser = subparsers.add_parser(
        "queue-info",
        help="List queue statistics (queue name, number of tasks in the queue, number of connected workers).",
    )
    queue_info.set_defaults(func=query_queues)
    queue_info.add_argument(
        "--dump",
        type=str,
        help="Dump the queue information to a file. Provide the filename (must be .csv or .json)",
        default=None,
    )
    queue_info.add_argument(
        "--specific-queues", nargs="+", type=str, help="Display queue stats for specific queues you list here"
    )
    queue_info.add_argument(
        "--task_server",
        type=str,
        default="celery",
        help="Task server type. Default: %(default)s",
    )
    spec_group = queue_info.add_argument_group("specification options")
    spec_group.add_argument(
        "--spec",
        dest="specification",
        type=str,
        help="Path to a Merlin YAML spec file. \
                            This will only display information for queues defined in this spec file. \
                            This is the same behavior as the status command prior to Merlin version 1.11.0.",
    )
    spec_group.add_argument(
        "--steps",
        nargs="+",
        type=str,
        dest="steps",
        default=["all"],
        help="The specific steps in the YAML file you want to query the queues of. "
        "This option MUST be used with the --spec option",
    )
    spec_group.add_argument(
        "--vars",
        action="store",
        dest="variables",
        type=str,
        nargs="+",
        default=None,
        help="Specify desired Merlin variable values to override those found in the specification. Space-delimited. "
        "This option MUST be used with the --spec option. Example: '--vars LEARN=path/to/new_learn.py EPOCHS=3'",
    )

    # merlin info
    info: ArgumentParser = subparsers.add_parser(
        "info",
        help="display info about the merlin configuration and the python configuration. Useful for debugging.",
    )
    info.set_defaults(func=print_info)


def main():
    """
    Entry point for the Merlin command-line interface (CLI) operations.

    This function sets up the argument parser, handles command-line arguments, 
    initializes logging, and executes the appropriate function based on the 
    provided command. It ensures that the user receives help information if 
    no arguments are provided and performs error handling for any exceptions 
    that may occur during command execution.
    """
    parser = setup_argparse()
    if len(sys.argv) == 1:
        parser.print_help(sys.stdout)
        return 1
    args = parser.parse_args()

    setup_logging(logger=LOG, log_level=args.level.upper(), colors=True)

    try:
        args.func(args)
        # pylint complains that this exception is too broad - being at the literal top of the program stack,
        # it's ok.
    except Exception as excpt:  # pylint: disable=broad-except
        LOG.debug(traceback.format_exc())
        LOG.error(str(excpt))
        sys.exit(1)
    # All paths in a function ought to return an exit code, or none of them should. Given the
    # distributed nature of Merlin, maybe it doesn't make sense for it to exit 0 until the work is completed, but
    # if the work is dispatched with no errors, that is a 'successful' Merlin run - any other failures are runtime.
    sys.exit()


if __name__ == "__main__":
    main()
