##############################################################################
# Copyright (c) Lawrence Livermore National Security, LLC and other Merlin
# Project developers. See top-level LICENSE and COPYRIGHT files for dates and
# other details. No copyright assignment is required to contribute to Merlin.
##############################################################################

"""
Mixin providing unified local execution and return code handling for all Merlin script adapters.

This module contains the `MerlinSubmissionMixin` class, which standardizes how all Merlin
script adapters execute workflow steps and handle return codes. Regardless of the scheduler
type they generate scripts for (SLURM, Flux, LSF, or local), all Merlin adapters execute
scripts locally within Celery worker processes. The mixin ensures consistent behavior by
providing a shared `submit()` method that handles process execution, output file management,
and conversion from standard exit codes to Merlin's specialized return code system for
workflow control (restart, retry, stop workers, etc.).
"""

import logging
import os
from typing import Dict

from maestrowf.datastructures.core.study import StudyStep
from maestrowf.interfaces.script import SubmissionRecord
from maestrowf.utils import start_process

from merlin.common.enums import ReturnCode


LOG = logging.getLogger(__name__)


# Pylint complains we only have one public method but this is a mixin class so we don't care
class MerlinSubmissionMixin:  # pylint: disable=too-few-public-methods
    """
    Mixin providing consistent local execution and return code handling for all Merlin adapters.

    This mixin class ensures all Merlin script adapters follow the same execution pattern:
    generating scheduler-appropriate scripts but executing them locally within Celery workers.
    It provides a unified `submit()` method that handles process execution, output file
    creation, and conversion from standard exit codes to Merlin's workflow control system.

    The mixin implements Merlin's hybrid execution model where adapters generate scripts with
    proper scheduler directives (e.g., flux run, srun, etc.) for environment compatibility,
    but execute them locally to maintain control over job distribution and workflow state.

    Usage:
        This mixin should be the first parent class in the inheritance hierarchy to ensure
        its `submit()` method takes precedence:

        ```python
        class MerlinSlurmScriptAdapter(MerlinSubmissionMixin, SlurmScriptAdapter):
            # submit() method provided by mixin - no override needed
        ```
    """

    def _execute_script(self, path: str, cwd: str, env: Dict = None) -> SubmissionRecord:
        """
        Execute a script locally and create a submission record with the results.

        This method handles the actual process execution for all Merlin adapters, providing
        consistent behavior regardless of the scheduler type the script was generated for.
        It uses Maestro's process utilities to execute the script and creates standardized
        output files following the same naming convention as LocalScriptAdapter.

        The method executes scripts locally even if they contain scheduler-specific commands
        like `srun`, `flux run`, or `jsrun`. Merlin does not need to schedule these scripts
        since the workers will already have been scheduled on HPC resources. If additional
        scheduling is needed, then the script adapters using this class will add scheduler-specific
        commands inside the script via LAUNCHER or VLAUNCHER.

        Args:
            path: Absolute path to the executable script file.
            cwd: Working directory where the script should be executed.
            env: Optional dictionary of environment variables to set for the process.
                If None, the current process environment is used.

        Returns:
            A `SubmissionRecord` containing the process exit code, process ID, and execution
                status. The record uses standard Maestro SubmissionCode values (OK/ERROR) based
                on whether the process could be started, with the actual exit code stored for
                later conversion to Merlin return codes.

        Example:
            Generated scripts might contain scheduler-specific commands:

            ```bash
            #!/bin/bash

            srun -n 16 simulation.exe input.dat
            ```

            This script executes locally, and if the worker is running within a SLURM
            allocation, the `srun` command will work correctly. If not, `srun` will
            fall back to local execution or fail appropriately.
        """
        # Pull out basename of the step
        script_basename = os.path.basename(path)
        new_output_name = os.path.splitext(script_basename)[0]

        # Execute the script using Maestro's start_process utility
        process = start_process(path, shell=False, cwd=cwd, env=env)
        output, err = process.communicate()
        retcode = process.wait()
        pid = process.pid

        # Create output files like LocalScriptAdapter does
        o_path = os.path.join(cwd, f"{new_output_name}.out")
        e_path = os.path.join(cwd, f"{new_output_name}.err")

        with open(o_path, "w") as out:
            out.write(output)

        with open(e_path, "w") as out:
            out.write(err)

        # Create and return submission record
        if retcode == 0:
            LOG.info("Execution returned status OK.")
            submission_record = SubmissionRecord(ReturnCode.OK, retcode, pid)
        else:
            LOG.warning(f"Execution returned an error: {str(err)}")
            submission_record = SubmissionRecord(ReturnCode.ERROR, retcode, pid)
            submission_record.add_info("stderr", str(err))

        return submission_record

    # Pylint has a lot to say about the arguments here but all necessary to conform to Maestro
    def submit(
        self, step: StudyStep, path: str, cwd: str, job_map: Dict = None, env: Dict = None
    ) -> SubmissionRecord:  # pylint: disable=too-many-arguments, too-many-positional-arguments, unused-argument
        """
        Execute a workflow step locally and handle Merlin-specific return code conversion.

        This is the main entry point for executing workflow steps in Merlin. It provides
        a consistent interface across all adapter types, executing scripts locally while
        handling Merlin's specialized return code system for workflow control. The method
        processes exit codes to determine appropriate workflow actions like restarting
        steps, retrying execution, or stopping workers.

        Args:
            step: The `StudyStep` instance containing workflow step information including
                name, description, and execution parameters.
            path: Absolute path to the generated script file to execute.
            cwd: Working directory for script execution, typically the step's workspace.
            job_map: Mapping of step names to job identifiers (unused in local execution
                but maintained for interface compatibility with Maestro adapters).
            env: Optional environment variables dictionary. If provided, these variables
                will be available to the executing script in addition to the current
                process environment.

        Returns:
            A `SubmissionRecord` with execution results and Merlin-specific return code.
                The record's `_subcode` attribute contains the interpreted Merlin ReturnCode,
                while the original process exit code is preserved in the `return_code` field.
        """
        LOG.debug(f"cwd = {cwd}")
        LOG.debug(f"Script to execute: {path}")
        LOG.debug(f"Starting process {path} in cwd {cwd} called {step.name}")

        # Execute the script locally using the same logic as LocalScriptAdapter
        submission_record = self._execute_script(path, cwd, env=env)

        # Handle return code
        retcode = submission_record.return_code
        if retcode == ReturnCode.OK:
            LOG.debug("Execution returned status OK.")
        elif retcode == ReturnCode.RESTART:
            LOG.debug("Execution returned status RESTART.")
            step.restart = True
        elif retcode == ReturnCode.SOFT_FAIL:
            LOG.warning("Execution returned status SOFT_FAIL. ")
        elif retcode == ReturnCode.HARD_FAIL:
            LOG.warning("Execution returned status HARD_FAIL. ")
        elif retcode == ReturnCode.RETRY:
            LOG.debug("Execution returned status RETRY.")
            step.restart = False
        elif retcode == ReturnCode.STOP_WORKERS:
            LOG.debug("Execution returned status STOP_WORKERS")
        elif retcode == ReturnCode.RAISE_ERROR:
            LOG.debug("Execution returned status RAISE_ERROR")
        else:
            LOG.warning(f"Unrecognized Merlin Return code: {retcode}, returning SOFT_FAIL")
            submission_record.add_info("retcode", retcode)
            retcode = ReturnCode.SOFT_FAIL

        # Currently, we use Maestro's execute method, which is returning the
        # submission code we want it to return the return code, so we are
        # setting it in here.
        # TODO: In the refactor/status branch we're overwriting Maestro's execute method (I think) so
        # we should be able to change this (i.e. add code in the overridden execute and remove this line)
        submission_record._subcode = retcode  # pylint: disable=W0212

        return submission_record
