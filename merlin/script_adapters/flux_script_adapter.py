##############################################################################
# Copyright (c) Lawrence Livermore National Security, LLC and other Merlin
# Project developers. See top-level LICENSE and COPYRIGHT files for dates and
# other details. No copyright assignment is required to contribute to Merlin.
##############################################################################

""" """

import logging
from typing import Dict, Set, Tuple, Union

from maestrowf.abstracts.enums import StepPriority
from maestrowf.datastructures.core.study import StudyStep

from merlin.script_adapters.slurm_script_adapter import (
    MerlinSlurmScriptAdapter,  # TODO replace this with Maestro flux script adapter
)
from merlin.script_adapters.submission_mixin import MerlinSubmissionMixin
from merlin.script_adapters.utils import setup_vlaunch
from merlin.utils import convert_timestring


LOG = logging.getLogger(__name__)


class MerlinFluxScriptAdapter(MerlinSubmissionMixin, MerlinSlurmScriptAdapter):
    """
    A `SchedulerScriptAdapter` class for flux blocking parallel launches.

    The `MerlinFluxScriptAdapter` is designed for workflows that execute flux parallel jobs
    in a Celery worker. It utilizes non-blocking submits and allows for configuration of the
    shell in which scripts are executed.

    Attributes:
        _cmd_flags (Dict[str, str]): A dictionary containing command-line flags for the flux command.
        _unsupported (Set[str]): A set of command flags that are not supported by this adapter.

    Methods:
        get_priority: Retrieves the priority of the step.
        time_format: Converts a time format to flux standard designation.
        write_script: Writes the script for the specified step and returns relevant paths.
    """

    def __init__(self, **kwargs: Dict):
        """
        Initialize an instance of the `MerinFluxScriptAdapter`.

        The `MerlinFluxScriptAdapter` is the adapter that is used for workflows that
        will execute flux parallel jobs in a celery worker. The only configurable aspect to
        this adapter is the shell that scripts are executed in.

        Args:
            **kwargs: A dictionary with default settings for the adapter.
        """
        # The flux_command should always be overriden by the study object's flux_command property
        flux_command = kwargs.pop("flux_command", "flux run")
        super().__init__(**kwargs)

        self._cmd_flags: Dict[str, str] = {
            "cmd": flux_command,
            "ntasks": "-n",
            "nodes": "-N",
            "cores per task": "-c",
            "gpus per task": "-g",
            "walltime": "-t",
            "flux": "",
        }  # noqa

        if "wreck" in flux_command:
            self._cmd_flags["walltime"] = "-T"

        new_unsupported = [
            "cmd",
            "ntasks",
            "nodes",
            "gpus",
            "reservation",
            "restart",
            "task_queue",
            "max_retries",
            "retry_delay",
            "pre",
            "post",
            "depends",
            "bind",
            "lsf",
            "slurm",
        ]
        self._unsupported: Set[str] = set(new_unsupported)  # noqa

    def get_priority(self, priority: StepPriority):
        """
        This is implemented to override the abstract method and fix a pylint error.

        Args:
            priority: Float or
                [`StepPriority`](https://maestrowf.readthedocs.io/en/latest/Maestro/reference_guide/api_reference/abstracts/enums/index.html#maestrowf.abstracts.enums.StepPriority)
                enum representing priorty.
        """

    def time_format(self, val: Union[str, int]) -> str:
        """
        Convert a time format to Flux Standard Duration (FSD).

        This method takes a time value and converts it into a format that is compatible
        with Flux's standard time representation. The conversion is performed using the
        [`convert_timestring`][utils.convert_timestring] function with the specified format
        method.

        Args:
            val: The time value to be converted. This can be a string representing a time
                duration or an integer representing a time value.

        Returns:
            The time formatted according to Flux Standard Duration (FSD).
        """
        return convert_timestring(val, format_method="FSD")

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
        setup_vlaunch(step.run, "flux", True)

        return super().write_script(ws_path, step)
