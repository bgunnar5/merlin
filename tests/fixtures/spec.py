"""
Fixtures specifically for help testing the modules in the spec/ directory.
"""

import pytest

from tests.fixture_types import FixtureCallable, FixtureStr


@pytest.fixture(scope="session")
def spec_testing_dir(create_testing_dir: FixtureCallable, temp_output_dir: FixtureStr) -> FixtureStr:
    """
    Fixture to create a temporary output directory for tests related to the functionality in the
    spec/ directory.

    Args:
        create_testing_dir: A fixture which returns a function that creates the testing directory.
        temp_output_dir: The path to the temporary output directory we'll be using for this test run.

    Returns:
        The path to the temporary testing directory for spec tests.
    """
    return create_testing_dir(temp_output_dir, "spec_testing")


@pytest.fixture(scope="session")
def spec_basic_ensemble_contents() -> FixtureStr:
    """
    Fixture that provides the contents of a basic ensemble configuration.

    This fixture returns a YAML string that describes a basic ensemble setup
    for running a specified number of "hello world" tasks. It includes
    configuration for batch processing, environment variables, and study
    parameters.

    Returns:
        A YAML string representing the basic ensemble configuration.
    """
    return """
description:
    name: basic_ensemble
    description: Run 100 hello worlds.

batch:
    type: local

env:
    variables:
        OUTPUT_PATH: ./studies
        HELLO: $(SPECROOT)/hello_world.py

study:
    - name: hello
      description: |
         process a sample with hello world
      run:
        cmd: |
          python $(HELLO) -outfile hello_world_output_$(merlin_sample_id).json $(X0) $(X1) $(X2)
        procs: 1
        nodes: 1
        task_queue: hello_queue

global.parameters:
    X2:
        values : [0.5]
        label  : X2.%%
    N_NEW:
        values : [100]
        label  : N_NEW.%%

merlin:
    samples:
        generate:
            cmd: python $(SPECROOT)/make_samples.py -n 100 -outfile=$(OUTPUT_PATH)/samples.npy
        file: $(OUTPUT_PATH)/samples.npy
        column_labels: [X0, X1]
"""


@pytest.fixture(scope="session")
def spec_basic_ensemble_no_merlin_contents() -> FixtureStr:
    """
    Fixture that provides the contents of a basic ensemble configuration without a `merlin` block.

    This fixture returns a YAML string that describes a basic ensemble setup
    for running a specified number of "hello world" tasks, but omits the
    Merlin-specific configuration. It includes batch processing settings,
    environment variables, and study parameters.

    Returns:
        A YAML string representing the basic ensemble configuration without a `merlin` block.
    """
    return """
description:
    name: basic_ensemble_no_merlin
    description: Run 100 hello worlds.

batch:
    type: local

env:
    variables:
        OUTPUT_PATH: ./studies
        HELLO: $(SPECROOT)/hello_world.py

study:
    - name: hello
      description: |
         process a sample with hello world
      run:
        cmd: |
          python $(HELLO) -outfile hello_world_output_$(merlin_sample_id).json $(X0) $(X1) $(X2)
        procs: 1
        nodes: 1
        task_queue: hello_queue

global.parameters:
    X2:
        values : [0.5]
        label  : X2.%%
    N_NEW:
        values : [100]
        label  : N_NEW.%%
"""


@pytest.fixture(scope="session")
def spec_basic_ensemble_invalid_merlin_contents() -> FixtureStr:
    """
    Fixture that provides the contents of a basic ensemble configuration with invalid Merlin data.

    This fixture returns a YAML string that serves as a template for testing
    the verification of custom `merlin` blocks. It includes a basic batch
    configuration and a study step that is not intended to run, along with
    a malformed `merlin` block.

    Returns:
        A YAML string representing the basic ensemble configuration with invalid Merlin data.
    """
    return """
description:
    name: basic_ensemble_invalid_merlin
    description: Template yaml to ensure our custom merlin block verification works as intended

batch:
    type: local

study:
    - name: step1
      description: |
         this won't actually run
      run:
        cmd: |
          echo "if this is printed something is bad"

merlin:
    resources:
        task_server: celery
        overlap: false
        workers:
            worker1:
                steps: []
"""


@pytest.fixture(scope="session")
def spec_create_ensemble_file() -> FixtureCallable:
    """
    Sets up a callable function for creating an ensemble file and returning
    the path to it.

    Returns:
        A fixture function that creates the ensemble file.
    """
    def _create_ensemble_file(spec_testing_dir: str, ensemble_str: str, filename: str) -> str:
        """
        The hidden function for creating an ensemble file.

        Args:
            spec_testing_dir: The path to the temporary testing directory for spec tests.
            ensemble_str: The contents that will be written to the ensemble file.
            filename: The name of the ensemble file to create.

        Returns:
            The path to the ensemble file.
        """
        spec_filepath = os.path.join(spec_testing_dir, filename)
        with open(spec_filepath, "w+") as _file:
            _file.write(ensemble_str)
        return spec_filepath
    return _create_ensemble_file


@pytest.fixture(scope="session")
def spec_basic_ensemble_file(spec_testing_dir: FixtureStr, spec_basic_ensemble_contents: FixtureStr):
    """
    """
    return create_ensemble_fixture(spec_testing_dir, spec_basic_ensemble_contents, "basic_ensemble.yaml")


@pytest.fixture(scope="session")
def spec_basic_ensemble_no_merlin_file(spec_testing_dir: FixtureStr, spec_basic_ensemble_no_merlin_contents: FixtureStr):
    """
    """
    return create_ensemble_fixture(spec_testing_dir, spec_basic_ensemble_no_merlin_contents, "basic_ensemble_no_merlin.yaml")


@pytest.fixture(scope="session")
def spec_basic_ensemble_invalid_merlin_file(spec_testing_dir: FixtureStr, spec_basic_ensemble_invalid_merlin_contents: FixtureStr):
    """
    """
    return create_ensemble_fixture(spec_testing_dir, spec_basic_ensemble_invalid_merlin_contents, "basic_ensemble_invalid_merlin.yaml")

