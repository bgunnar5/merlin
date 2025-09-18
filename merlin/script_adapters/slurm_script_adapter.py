##############################################################################
# Copyright (c) Lawrence Livermore National Security, LLC and other Merlin
# Project developers. See top-level LICENSE and COPYRIGHT files for dates and
# other details. No copyright assignment is required to contribute to Merlin.
##############################################################################


"""
Merlin SLURM script adapter for generating HPC-compatible workflow scripts.

This module provides the `MerlinSlurmScriptAdapter` class, which extends Maestro's
`SlurmScriptAdapter` to generate SLURM-compatible batch scripts while executing
them locally within Merlin's worker-based system. The adapter creates scripts with
proper SLURM directives, resource specifications, and parallel execution commands
suitable for High Performance Computing (HPC) environments.
"""

import logging
from typing import Dict, List, Set, Tuple, Union

from maestrowf.abstracts.enums import StepPriority
from maestrowf.datastructures.core.study import StudyStep
from maestrowf.interfaces.script.slurmscriptadapter import SlurmScriptAdapter

from merlin.script_adapters.submission_mixin import MerlinSubmissionMixin
from merlin.script_adapters.utils import setup_vlaunch
from merlin.utils import convert_timestring


LOG = logging.getLogger(__name__)


class MerlinSlurmScriptAdapter(MerlinSubmissionMixin, SlurmScriptAdapter):
    """
    Merlin script adapter for generating SLURM-compatible workflow scripts with local execution.

    This adapter extends Maestro's `SlurmScriptAdapter` to generate scripts with proper SLURM
    batch directives and parallel commands while executing them locally within Merlin's worker
    system. It creates HPC-ready scripts with srun commands that are compatible with SLURM-managed
    clusters, but executes these scripts directly in Celery workers rather than submitting them to
    a scheduler.

    Attributes:
        _cmd_flags (Dict[str, str]): A dictionary containing command flags for SLURM.
        _unsupported (Set[str]): A set of command flags that are not supported by this adapter.

    Methods:
        get_header: Generates the header for SLURM execution scripts.
        get_parallelize_command: Generates the SLURM parallelization segment of the command line.
        get_priority: Overrides the abstract method to fix a pylint error.
        time_format: Converts a timestring to HH:MM:SS format.
        write_script: Overwrites the write_script method from the base class to ensure VLAUNCHER compatibility.
    """

    def __init__(self, **kwargs: Dict):
        """
        Initialize an instance of the `MerinSlurmScriptAdapter`.

        The `MerlinSlurmScriptAdapter` is the adapter that is used for workflows that
        will execute SLURM parallel jobs in a celery worker. The only configurable aspect to
        this adapter is the shell that scripts are executed in.

        Args:
            **kwargs: A dictionary with default settings for the adapter.
        """
        super().__init__(**kwargs)

        self._cmd_flags: Dict[str, str]

        self._cmd_flags["slurm"] = ""
        self._cmd_flags["walltime"] = "-t"

        new_unsupported: List[str] = [
            "bind",
            "flux",
            "gpus per task",
            "gpus",
            "lsf",
            "max_retries",
            "post",
            "pre",
            "restart",
            "retry_delay",
            "shell",
            "task_queue",
        ]
        self._unsupported: Set[str] = set(list(self._unsupported) + new_unsupported)

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
        Generate the header present at the top of Slurm execution scripts.

        Args:
            step: A Maestro StudyStep instance that contains parameters relevant to the execution.

        Returns:
            A string of the header based on internal batch parameters and the parameter step.
        """
        return f"#!{self._exec}"

    def time_format(self, val: Union[str, int]) -> str:
        """
        Convert the input timestring or integer to HH:MM:SS format.

        This method utilizes the [`convert_timestring`][utils.convert_timestring]
        function to convert a given timestring or integer (representing seconds)
        into a formatted string in the 'hours:minutes:seconds' (HH:MM:SS) format.

        Args:
            val: A timestring in the format '[days]:[hours]:[minutes]:seconds' or
                an integer representing time in seconds.

        Returns:
            A string representation of the input time formatted as 'HH:MM:SS'.
        """
        return convert_timestring(val, format_method="HMS")

    def get_parallelize_command(self, procs: int, nodes: int = None, **kwargs: Dict) -> str:
        """
        Generate the SLURM parallelization segment of the command line.

        This method constructs the command line segment required for parallel execution
        in SLURM, including the number of processors and nodes to allocate. It also
        incorporates any additional supported command flags provided in `kwargs`.

        Args:
            procs: The number of processors to allocate for the parallel call.
            nodes: The number of nodes to allocate for the parallel call (default is 1).
            **kwargs: Additional command flags to customize the SLURM command.
                Supported flags include 'walltime' and others defined in the
                `_cmd_flags` attribute, excluding those in the `_unsupported` set.

        Returns:
            A string representing the SLURM parallelization command, formatted with the
                specified number of processors, nodes, and any additional flags.
        """
        args = [
            # SLURM srun command
            self._cmd_flags["cmd"],
            # Processors segment
            self._cmd_flags["ntasks"],
            str(procs),
        ]

        if nodes:
            args += [self._cmd_flags["nodes"], str(nodes)]

        supported = set(kwargs.keys()) - self._unsupported
        for key in supported:
            value = kwargs.get(key)
            if not value:
                continue

            if key not in self._cmd_flags:
                LOG.warning("'%s' is not supported -- ommitted.", key)
                continue

            if key == "walltime":
                args += [
                    self._cmd_flags[key],
                    f"{str(self.time_format(value))}",
                ]
            elif "=" in self._cmd_flags[key]:
                args += [f"{self._cmd_flags[key]}{str(value)}"]
            else:
                args += [self._cmd_flags[key], f"{str(value)}"]

        return " ".join(args)

    def write_script(self, ws_path: str, step: StudyStep) -> Tuple[bool, str, str]:
        """
        This will overwrite the `write_script` method from Maestro's base ScriptAdapter
        class but will eventually call it. This is necessary for the VLAUNCHER to work.

        Args:
            ws_path: The path to the workspace where the scripts will be written.
            step: The Maestro `StudyStep` object containing information for the step.

        Returns:
            A tuple containing:\n
                - bool: A boolean indicating whether this step is to be scheduled or not.
                        (Merlin can ignore this value.)
                - str: The path to the script for the command.
                - str: The path to the script for the restart command.
        """
        setup_vlaunch(step.run, "slurm", False)

        return super().write_script(ws_path, step)
