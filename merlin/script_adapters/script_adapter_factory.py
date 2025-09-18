##############################################################################
# Copyright (c) Lawrence Livermore National Security, LLC and other Merlin
# Project developers. See top-level LICENSE and COPYRIGHT files for dates and
# other details. No copyright assignment is required to contribute to Merlin.
##############################################################################

# TODO update this docstring in Merlin 2.0
"""
Factory module for creating Merlin script adapters.

This module provides the `MerlinScriptAdapterFactory` class, which serves as a
centralized registry and factory for all Merlin script adapters. The factory
abstracts the creation of appropriate script adapters based on scheduler type,
while ensuring all adapters use consistent execution patterns within Merlin's
worker-based architecture.
"""

import logging
from typing import Dict, List

from maestrowf.abstracts.interfaces.scriptadapter import ScriptAdapter

from merlin.script_adapters import (
    MerlinFluxScriptAdapter,
    MerlinLocalScriptAdapter,
    MerlinLSFScriptAdapter,
    MerlinSlurmScriptAdapter,
)


LOG = logging.getLogger(__name__)


# TODO in Merlin 2.0 update this to use the abstract factory
class MerlinScriptAdapterFactory:
    """
    This class routes to the correct `ScriptAdapter`.

    The `MerlinScriptAdapterFactory` is responsible for providing the appropriate
    `ScriptAdapter` based on the specified adapter ID. It maintains a mapping of
    available adapters and offers methods to retrieve them.

    Attributes:
        factories: A dictionary mapping adapter IDs (str) to their corresponding
            `ScriptAdapter` classes.

    Methods:
        get_adapter: Returns the appropriate `ScriptAdapter` class for the given adapter ID.
        get_valid_adapters: Returns a list of valid adapter IDs that can be used with this factory.
    """

    factories: Dict[str, ScriptAdapter] = {
        "flux": MerlinFluxScriptAdapter,
        "lsf": MerlinLSFScriptAdapter,
        "slurm": MerlinSlurmScriptAdapter,
        "local": MerlinLocalScriptAdapter,
    }

    @classmethod
    def get_adapter(cls, adapter_id: str) -> ScriptAdapter:
        """
        Returns the appropriate `ScriptAdapter` to use.

        This method retrieves the `ScriptAdapter` class associated with the given
        adapter ID. If the adapter ID is not found in the factory's mapping,
        a ValueError is raised.

        Args:
            adapter_id: The ID of the desired `ScriptAdapter`.

        Returns:
            The corresponding `ScriptAdapter` class.

        Raises:
            ValueError: If the specified adapter_id is not found in the factories.
        """
        if adapter_id.lower() not in cls.factories:
            msg = f"""Adapter '{str(adapter_id)}' not found. Specify an adapter that exists
                or implement a new one mapping to the '{str(adapter_id)}'"""
            LOG.error(msg)
            raise ValueError(msg)

        return cls.factories[adapter_id]

    @classmethod
    def get_valid_adapters(cls) -> List[str]:
        """
        Returns the valid ScriptAdapters.

        This method provides a list of all valid adapter IDs that can be used
        with this factory. The IDs are derived from the keys of the factories
        dictionary.

        Returns:
            A list of valid adapter IDs.
        """
        return cls.factories.keys()
