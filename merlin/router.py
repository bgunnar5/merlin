###############################################################################
# Copyright (c) 2023, Lawrence Livermore National Security, LLC.
# Produced at the Lawrence Livermore National Laboratory
# Written by the Merlin dev team, listed in the CONTRIBUTORS file.
# <merlin@llnl.gov>
#
# LLNL-CODE-797170
# All rights reserved.
# This file is part of Merlin, Version: 1.10.2.
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

"""
This module routes actions from the Merlin CLI to the appropriate tasking
logic.

This module is intended to help keep the task management layer (i.e., Celery)
decoupled from the logic the tasks are running.
"""
import logging
import os
import time
from typing import List, Optional, Tuple

from merlin.study.celeryadapter import (
    build_set_of_queues,
    create_celery_config,
    dump_celery_queue_info,
    get_workers_from_app,
    purge_celery_tasks,
    query_celery_queues,
    query_celery_workers,
    run_celery,
    start_celery_workers,
    stop_celery_workers,
)


try:
    from importlib import resources
except ImportError:
    import importlib_resources as resources


LOG = logging.getLogger(__name__)

# TODO go through this file and find a way to make a common return format to main.py
# Also, if that doesn't fix them, look into the pylint errors that have been disabled
# and try to resolve them


def run_task_server(study, run_mode=None):
    """
    Creates the task server interface for communicating the tasks.

    :param `study`: The MerlinStudy object
    :param `run_mode`: The type of run mode, e.g. local, batch
    """
    if study.expanded_spec.merlin["resources"]["task_server"] == "celery":
        run_celery(study, run_mode)
    else:
        LOG.error("Celery is not specified as the task server!")


def launch_workers(spec, steps, worker_args="", disable_logs=False, just_return_command=False):
    """
    Launches workers for the specified study.

    :param `specs`: Tuple of (YAMLSpecification, MerlinSpec)
    :param `steps`: The steps in the spec to tie the workers to
    :param `worker_args`: Optional arguments for the workers
    :param `disable_logs`: Boolean flag to disable the worker logs from celery
    :param `just_return_command`: Don't execute, just return the command
    """
    if spec.merlin["resources"]["task_server"] == "celery":  # pylint: disable=R1705
        # Start workers
        cproc = start_celery_workers(spec, steps, worker_args, disable_logs, just_return_command)
        return cproc
    else:
        LOG.error("Celery is not specified as the task server!")
        return "No workers started"


def purge_tasks(task_server, spec, force, steps):
    """
    Purges all tasks.

    :param `task_server`: The task server from which to purge tasks.
    :param `spec`: A MerlinSpec object
    :param `force`: Purge without asking for confirmation
    :param `steps`: Space-separated list of stepnames defining queues to purge,
        default is all steps
    """
    LOG.info(f"Purging queues for steps = {steps}")

    if task_server == "celery":  # pylint: disable=R1705
        queues = spec.make_queue_string(steps)
        # Purge tasks
        return purge_celery_tasks(queues, force)
    else:
        LOG.error("Celery is not specified as the task server!")
        return -1


def dump_queue_info(task_server: str, query_return: List[Tuple[str, int, int]], dump_file: str):
    """
    Format the information we're going to dump in a way that the Dumper class can
    understand and add a timestamp to the info.

    :param `task_server`: The task server from which to query queues
    :param `query_return`: The output of query_queues
    :param `dump_file`: The filepath of the file we'll dump queue info to
    """
    if task_server == "celery":
        dump_celery_queue_info(query_return, dump_file)
    else:
        LOG.error("Celery is not specified as the task server!")


def query_queues(
    task_server: str,
    spec: "MerlinSpec",  # noqa: F821
    steps: List[str],
    specific_queues: List[str],
    verbose: Optional[bool] = True,
):
    """
    Queries status of queues.

    :param `task_server`: The task server from which to query queues
    :param `spec`: A MerlinSpec object or None
    :param `steps`: Spaced-separated list of stepnames to query. Default is all
    :param `specific_queues`: A list of queue names to query or None
    :param `verbose`: A bool to determine whether to output log statements or not
    """
    if task_server == "celery":  # pylint: disable=R1705
        # Build a set of queues to query and query them
        queues = build_set_of_queues(spec, steps, specific_queues, verbose=verbose)
        return query_celery_queues(queues)
    else:
        LOG.error("Celery is not specified as the task server!")
        return []


def query_workers(task_server, spec_worker_names, queues, workers_regex):
    """
    Gets info from workers.

    :param `task_server`: The task server to query.
    """
    LOG.info("Searching for workers...")

    if task_server == "celery":
        query_celery_workers(spec_worker_names, queues, workers_regex)
    else:
        LOG.error("Celery is not specified as the task server!")


def get_workers(task_server):
    """Get all workers.

    :param `task_server`: The task server to query.
    :return: A list of all connected workers
    :rtype: list
    """
    if task_server == "celery":  # pylint: disable=R1705
        return get_workers_from_app()
    else:
        LOG.error("Celery is not specified as the task server!")
        return []


def stop_workers(task_server, spec_worker_names, queues, workers_regex):
    """
    Stops workers.

    :param `task_server`: The task server from which to stop workers.
    :param `spec_worker_names`: Worker names to stop, drawn from a spec.
    :param `queues`     : The queues to stop
    :param `workers_regex`    : Regex for workers to stop
    """
    LOG.info("Stopping workers...")

    if task_server == "celery":  # pylint: disable=R1705
        # Stop workers
        stop_celery_workers(queues, spec_worker_names, workers_regex)
    else:
        LOG.error("Celery is not specified as the task server!")


def create_config(task_server: str, config_dir: str, broker: str, test: str) -> None:
    """
    Create a config for the given task server.

    :param [str] `task_server`: The task server from which to stop workers.
    :param [str] `config_dir`: Optional directory to install the config.
    :param [str] `broker`: string indicated the broker, used to check for redis.
    :param [str] `test`: string indicating if the app.yaml is used for testing.
    """
    if test:
        LOG.info("Creating test config ...")
    else:
        LOG.info("Creating config ...")

    if not os.path.isdir(config_dir):
        os.makedirs(config_dir)

    if task_server == "celery":
        config_file = "app.yaml"
        data_config_file = "app.yaml"
        if broker == "redis":
            data_config_file = "app_redis.yaml"
        elif test:
            data_config_file = "app_test.yaml"
        with resources.path("merlin.data.celery", data_config_file) as data_file:
            create_celery_config(config_dir, config_file, data_file)
    else:
        LOG.error("Only celery can be configured currently.")


def check_merlin_status(args, spec):
    """
    Function to check merlin workers and queues to keep
    the allocation alive

    :param `args`: parsed CLI arguments
    :param `spec`: the parsed spec.yaml
    """
    queue_status = query_queues(args.task_server, spec, args.steps, None, verbose=False)

    total_jobs = 0
    total_consumers = 0
    for _, jobs, consumers in queue_status:
        total_jobs += jobs
        total_consumers += consumers

    if total_jobs > 0 and total_consumers == 0:
        # Determine if any of the workers are on this allocation
        worker_names = spec.get_worker_names()

        # Loop until workers are detected.
        count = 0
        max_count = 10
        while count < max_count:
            # This list will include strings comprised of the worker name with the hostname e.g. worker_name@host.
            worker_status = get_workers(args.task_server)
            LOG.info(f"Monitor: checking for workers, running workers = {worker_status} ...")

            check = any(any(iwn in iws for iws in worker_status) for iwn in worker_names)
            if check:
                break

            count += 1
            time.sleep(args.sleep)

        if count == max_count:
            LOG.error("Monitor: no workers available to process the non-empty queue")
            total_jobs = 0

    return total_jobs
