##############################################################################
# Copyright (c) Lawrence Livermore National Security, LLC and other Merlin
# Project developers. See top-level LICENSE and COPYRIGHT files for dates and
# other details. No copyright assignment is required to contribute to Merlin.
##############################################################################

"""
Utility functions for Merlin script adapter functionality.
"""

import logging

from merlin.utils import find_vlaunch_var


LOG = logging.getLogger(__name__)


def setup_vlaunch(step_run: str, batch_type: str, gpu_config: bool):
    """
    Check for the VLAUNCHER keyword in the step run string and configure VLAUNCHER settings.

    This function examines the provided step run command string for the presence of the
    VLAUNCHER keyword. If found, it replaces the keyword with the LAUNCHER keyword and
    extracts relevant MERLIN variables such as nodes, processes, and cores per task.
    It also configures GPU settings based on the provided boolean flag.

    Args:
        step_run: The step.run command string that may contain the VLAUNCHER keyword.
        batch_type: A string representing the type of batch processing being used.
        gpu_config: A boolean indicating whether GPUs should be configured.
    """
    if "$(VLAUNCHER)" in step_run["cmd"]:
        step_run["cmd"] = step_run["cmd"].replace("$(VLAUNCHER)", "$(LAUNCHER)")

        step_run["nodes"] = find_vlaunch_var("NODES", step_run["cmd"])
        step_run["procs"] = find_vlaunch_var("PROCS", step_run["cmd"])
        step_run["cores per task"] = find_vlaunch_var("CORES", step_run["cmd"])

        if find_vlaunch_var("GPUS", step_run["cmd"]):
            if gpu_config:
                step_run["gpus"] = find_vlaunch_var("GPUS", step_run["cmd"])
            else:
                LOG.warning(f"Merlin does not yet have the ability to set GPUs per task with {batch_type}. Coming soon.")
