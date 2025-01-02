###############################################################################
# Copyright (c) 2023, Lawrence Livermore National Security, LLC.
# Produced at the Lawrence Livermore National Laboratory
# Written by the Merlin dev team, listed in the CONTRIBUTORS file.
# <merlin@llnl.gov>
#
# LLNL-CODE-797170
# All rights reserved.
# This file is part of Merlin, Version: 1.12.1.
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
import logging
import subprocess
from typing import List, Tuple

import psutil

from merlin.managers.celerymanager import WORKER_INFO, CeleryManager, WorkerStatus
from merlin.spec.specification import MerlinSpec
from merlin.utils import verify_filepath


LOG = logging.getLogger(__name__)


def add_monitor_workers(workers: List[Tuple[str, str]]):
    """
    Adds workers to be monitored by the celery manager.
    
    Args:
        workers: A list of tuples which includes (worker_name, pid)
    """
    if workers is None or len(workers) <= 0:
        return

    LOG.info(
        f"MANAGER: Attempting to have the manager monitor the following workers {[worker_name for worker_name in workers]}."
    )
    monitored_workers = []

    with CeleryManager.get_worker_status_redis_connection() as redis_connection:
        for worker in workers:
            LOG.debug(f"MANAGER: Checking if connection for worker '{worker}' exists...")
            if redis_connection.exists(worker[0]):
                LOG.debug(f"MANAGER: Connection for worker '{worker}' exists. Setting this worker to be monitored")
                redis_connection.hset(worker[0], "monitored", 1)
                redis_connection.hset(worker[0], "pid", worker[1])
                monitored_workers.append(worker[0])
            else:
                LOG.debug(f"MANAGER: Connection for worker '{worker}' does not exist. Not monitoring this worker.")
            worker_info = WORKER_INFO
            worker_info["pid"] = worker[1]
            redis_connection.hmset(name=worker[0], mapping=worker_info)
    LOG.info(f"MANAGER: Manager is monitoring the following workers {monitored_workers}.")


def remove_monitor_workers(workers: List[str], worker_status: WorkerStatus = None, purge_entries: bool = True):
    """
    Remove specific workers from being monitored by the celery manager.

    Args:
        workers: A list of workers to stop monitoring.
        worker_status: A [`WorkerStatus`][merlin.managers.celerymanager.WorkerStatus] to set for the
            workers we're unmonitoring.
        purge_entries: A flag that signifies whether to delete the worker entries
            from the Redis database or not.
    """
    if workers is None or len(workers) <= 0:
        return

    with CeleryManager.get_worker_status_redis_connection() as redis_connection:
        for worker_pattern in workers:
            # Grab the matching workers from the Redis database
            matching_workers = redis_connection.keys(f"*{worker_pattern}*")
            LOG.debug(f"MANAGER: matching workers: {matching_workers}")
            for worker in matching_workers:
                worker_exists = redis_connection.exists(worker)
                LOG.debug(f"{worker} exists: {worker_exists}")
                LOG.debug(f"worker {worker} monitored (before unwatch) - {redis_connection.hget(worker, 'monitored')}")
        
                # If the worker exists, remove it from being monitored
                if worker_exists:
                    redis_connection.hset(worker, "monitored", 0)

                    # Set the worker status if specified
                    if worker_status is not None:
                        redis_connection.hset(worker, "status", worker_status)

                    # Delete the worker from both the status and worker args databases
                    if purge_entries:
                        redis_connection.delete(worker)
                        with CeleryManager.get_worker_args_redis_connection() as worker_args_connection:
                            worker_args_connection.delete(worker, f"{worker}_env")

                LOG.debug(f"worker {worker} monitored (after unwatch) - {redis_connection.hget(worker, 'monitored')}")


def is_manager_runnning() -> bool:
    """
    Check to see if the manager is running

    :return: True if manager is running and False if not.
    """
    with CeleryManager.get_worker_args_redis_connection() as redis_connection:
        manager_status = redis_connection.hgetall("manager")
    return manager_status["status"] == WorkerStatus.running and psutil.pid_exists(manager_status["pid"])


def run_manager(query_frequency: int = 60, query_timeout: float = 0.5, worker_timeout: int = 180, loop_condition: bool = True) -> bool:
    """
    A process locking function that calls the celery manager with proper arguments.

    :param query_frequency:     The frequency at which workers will be queried with ping commands
    :param query_timeout:       The timeout for the query pings that are sent to workers
    :param worker_timeout:      The sum total(query_frequency*tries) time before an attempt is made to restart worker.
    """
    celerymanager = CeleryManager(query_frequency=query_frequency, query_timeout=query_timeout, worker_timeout=worker_timeout)
    celerymanager.run(loop_condition=loop_condition)


def start_manager(query_frequency: int = 60, query_timeout: float = 0.5, worker_timeout: int = 180) -> bool:
    """
    A Non-locking function that calls the celery manager with proper arguments.

    :param query_frequency:     The frequency at which workers will be queried with ping commands
    :param query_timeout:       The timeout for the query pings that are sent to workers
    :param worker_timeout:      The sum total(query_frequency*tries) time before an attempt is made to restart worker.
    :return bool:               True if the manager was started successfully.
    """
    subprocess.Popen(
        f"merlin manager run -qf {query_frequency} -qt {query_timeout} -wt {worker_timeout}",
        shell=True,
        close_fds=True,
        stdout=subprocess.PIPE,
    )
    return True


def stop_manager() -> bool:
    """
    Stop the manager process using it's pid.

    :return bool:       True if the manager was stopped successfully and False otherwise.
    """
    with CeleryManager.get_worker_status_redis_connection() as redis_connection:
        LOG.debug(f"MANAGER: manager keys: {redis_connection.hgetall('manager')}")
        manager_pid = int(redis_connection.hget("manager", "pid"))
        manager_status = redis_connection.hget("manager", "status")
        LOG.debug(f"MANAGER: manager_status: {manager_status}")
        LOG.debug(f"MANAGER: pid exists: {psutil.pid_exists(manager_pid)}")

    # Check to make sure that the manager is running and the pid exists
    if manager_status == WorkerStatus.running and psutil.pid_exists(manager_pid):
        psutil.Process(manager_pid).terminate()
        return True
    return False


def resolve_workers(workers: List[str]) -> List[str]:
    """
    Resolve the list of workers, checking if the first entry is a specification file.

    Args:
        workers (List[str]): A list of worker names or a specification file.

    Returns:
        The resolved list of worker names.
    """
    # Load the worker names from the spec file (if provided)
    if len(workers) == 1 and workers[0].endswith(".yaml"):
        spec_file = verify_filepath(spec_filepath)
        spec = MerlinSpec.load_specification(spec_file)
        return spec.get_worker_names()

    # Otherwise, user gave us a list of workers
    return workers


def watch_workers(workers: List[str]):
    """
    Start monitoring the specified workers.

    Args:
        workers: A list of worker names or a specification file.
    """
    resolved_workers = resolve_workers(workers)
    add_monitor_workers(resolved_workers)


def unwatch_all_workers(purge_entries: bool = True):
    """
    Remove all workers from being monitored by the celery manager.

    Args:
        purge_entries: A flag that signifies whether to delete the worker entries
            from the Redis database or not.
    """
    with CeleryManager.get_worker_status_redis_connection() as redis_connection:
        # Retrieve all keys that represent monitored workers
        workers = redis_connection.keys()
        workers.remove("manager")

        # If there are no workers in the Redis database, return early
        if not workers:
            LOG.warning("MANAGER: No workers exist in the Redis database.")
            return

        # Call the remove_monitor_workers function to unmonitor all workers
        LOG.info(f"MANAGER: Unwatching the following workers - {workers}")
        remove_monitor_workers(workers, purge_entries=purge_entries)


def unwatch_workers(workers: List[str], purge_entries: bool):
    """
    Stop monitoring the specified workers.

    Args:
        workers: A list of worker names (or 'all') or a specification file.
        purge_entries: A flag that signifies whether to delete the worker entries
            from the Redis database or not.
    """
    if workers[0] == "all":  # Unwatch all workers
        unwatch_all_workers(purge_entries=purge_entries)
    else:  # Unwatch specific workers
        resolved_workers = resolve_workers(workers)
        remove_monitor_workers(resolved_workers, purge_entries=purge_entries)
