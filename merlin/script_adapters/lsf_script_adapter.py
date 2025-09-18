##############################################################################
# Copyright (c) Lawrence Livermore National Security, LLC and other Merlin
# Project developers. See top-level LICENSE and COPYRIGHT files for dates and
# other details. No copyright assignment is required to contribute to Merlin.
##############################################################################

""" """

import logging
from typing import Dict, Set, Tuple

from maestrowf.abstracts.enums import StepPriority
from maestrowf.datastructures.core.study import StudyStep
from maestrowf.interfaces.script.lsfscriptadapter import LSFScriptAdapter

from merlin.script_adapters.submission_mixin import MerlinSubmissionMixin
from merlin.script_adapters.utils import setup_vlaunch


LOG = logging.getLogger(__name__)


class MerlinLSFScriptAdapter(MerlinSubmissionMixin, LSFScriptAdapter):
    """
    A `SchedulerScriptAdapter` class for SLURM blocking parallel launches.
    The `MerlinLSFScriptAdapter` uses non-blocking submits for executing LSF parallel jobs
    in a Celery worker.

    Attributes:
        _cmd_flags (Dict[str, str]): A dictionary containing command flags for LSF execution.
        _unsupported (Set[str]): A set of parameters that are unsupported by this adapter.

    Methods:
        get_header: Generates the header for LSF execution scripts.
        get_parallelize_command: Generates the LSF parallelization segment of the command line.
        get_priority: Overrides the abstract method to fix a pylint error.
        write_script: Overwrites the write_script method from the base ScriptAdapter class.
    """

    def __init__(self, **kwargs: Dict):
        """
        Initialize an instance of the `MerinLSFScriptAdapter`.

        The `MerlinLSFScriptAdapter` is the adapter that is used for workflows that
        will execute LSF parallel jobs in a celery worker. The only configurable aspect to
        this adapter is the shell that scripts are executed in.

        Args:
            **kwargs: A dictionary with default settings for the adapter.
        """
        super().__init__(**kwargs)

        self._cmd_flags: Dict[str, str] = {
            "cmd": "jsrun",
            "ntasks": "--np",
            "nodes": "--nrs",
            "cores per task": "-c",
            "gpus per task": "-g",
            "num resource set": "--nrs",
            "bind": "-b",
            "launch_distribution": "-d",
            "exit_on_error": "-X",
            "lsf": "",
        }

        self._unsupported: Set[str] = {
            "cmd",
            "depends",
            "flux",
            "gpus",
            "max_retries",
            "nodes",
            "ntasks",
            "post",
            "pre",
            "reservation",
            "restart",
            "retry_delay",
            "shell",
            "slurm",
            "task_queue",
            "walltime",
        }

        self._extension = "sh"

    def get_priority(self, priority: StepPriority):
        """
        This is implemented to override the abstract method and fix a pylint error.

        Args:
            priority: Float or
                [`StepPriority`](https://maestrowf.readthedocs.io/en/latest/Maestro/reference_guide/api_reference/abstracts/enums/index.html#maestrowf.abstracts.enums.StepPriority)
                enum representing priorty.
        """

    def get_header(self, step: StudyStep) -> str:
        """
        Generate the header present at the top of LSF execution scripts.

        Args:
            step: A Maestro StudyStep instance that contains parameters relevant to the execution.

        Returns:
            A string of the header based on internal batch parameters and the parameter step.
        """
        return f"#!{self._exec}"

    def get_parallelize_command(self, procs: int, nodes: int = None, **kwargs: Dict) -> str:
        """
        Generate the LSF parallelization segment of the command line.

        This method constructs a command line segment for parallel execution in LSF.
        It allows specifying the number of processors and nodes to be allocated for the parallel call,
        along with additional command flags through keyword arguments.

        Args:
            procs: Number of processors to allocate to the parallel call.
            nodes: Number of nodes to allocate to the parallel call. Defaults to 1.
            **kwargs: Additional command flags that may be supported by the LSF command.

        Returns:
            A string representing the parallelization command configured using nodes and procs.
        """
        if not nodes:
            nodes = 1

        args = [
            # LSF jsrun command
            self._cmd_flags["cmd"],
            # Processors segment
            self._cmd_flags["ntasks"],
            str(procs),
            # Resource segment
            self._cmd_flags["nodes"],
            str(nodes),
        ]

        args += [self._cmd_flags["bind"], kwargs.pop("bind", "rs")]

        plane_cpus = int(int(procs) / int(nodes))
        args += [
            self._cmd_flags["launch_distribution"],
            kwargs.pop("launch_distribution", f"plane:{plane_cpus}"),
        ]

        args += [self._cmd_flags["exit_on_error"], kwargs.pop("exit_on_error", "1")]

        supported = set(kwargs.keys()) - self._unsupported
        for key in supported:
            value = kwargs.get(key)
            if key not in self._cmd_flags:
                LOG.warning("'%s' is not supported -- ommitted.", key)
                continue
            if value:
                args += [self._cmd_flags[key], f"{str(value)}"]

        return " ".join(args)

    def write_script(self, ws_path: str, step: StudyStep) -> Tuple[bool, str, str]:
        """
        This will overwrite the `write_script` method from Maestro's base ScriptAdapter
        class but will eventually call it. This is necessary for the VLAUNCHER to work.

        Args:
            ws_path: The path to the workspace where the scripts will be written.
            step: The Maestro StudyStep object containing information for the step.

        Returns:
            A tuple containing:\n
                - bool: A boolean indicating whether this step is to be scheduled or not.
                        (Merlin can ignore this value.)
                - str: The path to the script for the command.
                - str: The path to the script for the restart command.
        """
        setup_vlaunch(step.run, "lsf", False)

        return super().write_script(ws_path, step)
