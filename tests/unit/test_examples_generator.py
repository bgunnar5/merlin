"""
Tests for the `merlin/examples/generator.py` module.
"""
import os
import pathlib
from typing import List

from tabulate import tabulate

from merlin.examples.generator import (
    EXAMPLES_DIR,
    gather_all_examples,
    gather_example_dirs,
    list_examples,
    setup_example,
    write_example
)
from tests.utils import create_dir


EXAMPLES_GENERATOR_DIR = "{temp_output_dir}/examples_generator"


def test_gather_example_dirs():
    """Test the `gather_example_dirs` function."""
    example_workflows = [
        "feature_demo",
        "flux",
        "hello",
        "hpc_demo",
        "iterative_demo",
        "lsf",
        "null_spec",
        "openfoam_wf",
        "openfoam_wf_no_docker",
        "openfoam_wf_singularity",
        "optimization",
        "remote_feature_demo",
        "restart",
        "restart_delay",
        "simple_chain",
        "slurm"
    ]
    expected = {}
    for wf_dir in example_workflows:
        expected[wf_dir] = wf_dir
    actual = gather_example_dirs()
    assert actual == expected


def test_gather_all_examples():
    """Test the `gather_all_examples` function."""
    expected = [
        f"{EXAMPLES_DIR}/feature_demo/feature_demo.yaml",
        f"{EXAMPLES_DIR}/flux/flux_local.yaml",
        f"{EXAMPLES_DIR}/flux/flux_par_restart.yaml",
        f"{EXAMPLES_DIR}/flux/flux_par.yaml",
        f"{EXAMPLES_DIR}/flux/paper.yaml",
        f"{EXAMPLES_DIR}/hello/hello_samples.yaml",
        f"{EXAMPLES_DIR}/hello/hello.yaml",
        f"{EXAMPLES_DIR}/hello/my_hello.yaml",
        f"{EXAMPLES_DIR}/hpc_demo/hpc_demo.yaml",
        f"{EXAMPLES_DIR}/iterative_demo/iterative_demo.yaml",
        f"{EXAMPLES_DIR}/lsf/lsf_par_srun.yaml",
        f"{EXAMPLES_DIR}/lsf/lsf_par.yaml",
        f"{EXAMPLES_DIR}/null_spec/null_chain.yaml",
        f"{EXAMPLES_DIR}/null_spec/null_spec.yaml",
        f"{EXAMPLES_DIR}/openfoam_wf/openfoam_wf_template.yaml",
        f"{EXAMPLES_DIR}/openfoam_wf/openfoam_wf.yaml",
        f"{EXAMPLES_DIR}/openfoam_wf_no_docker/openfoam_wf_no_docker_template.yaml",
        f"{EXAMPLES_DIR}/openfoam_wf_no_docker/openfoam_wf_no_docker.yaml",
        f"{EXAMPLES_DIR}/openfoam_wf_singularity/openfoam_wf_singularity.yaml",
        f"{EXAMPLES_DIR}/optimization/optimization_basic.yaml",
        f"{EXAMPLES_DIR}/remote_feature_demo/remote_feature_demo.yaml",
        f"{EXAMPLES_DIR}/restart/restart.yaml",
        f"{EXAMPLES_DIR}/restart_delay/restart_delay.yaml",
        f"{EXAMPLES_DIR}/simple_chain/simple_chain.yaml",
        f"{EXAMPLES_DIR}/slurm/slurm_par_restart.yaml",
        f"{EXAMPLES_DIR}/slurm/slurm_par.yaml"
    ]
    actual = gather_all_examples()
    assert sorted(actual) == sorted(expected)


def test_write_example_dir(temp_output_dir: str):
    """
    Test the `write_example` function with the src_path as a directory.
    
    :param temp_output_dir: The path to the temporary output directory we'll be using for this test run
    """
    generator_dir = EXAMPLES_GENERATOR_DIR.format(temp_output_dir=temp_output_dir)
    dir_to_copy = f"{EXAMPLES_DIR}/feature_demo/"

    write_example(dir_to_copy, generator_dir)
    assert sorted(os.listdir(dir_to_copy)) == sorted(os.listdir(generator_dir))


def test_write_example_file(temp_output_dir: str):
    """
    Test the `write_example` function with the src_path as a file.
    
    :param temp_output_dir: The path to the temporary output directory we'll be using for this test run
    """
    generator_dir = EXAMPLES_GENERATOR_DIR.format(temp_output_dir=temp_output_dir)
    create_dir(generator_dir)

    dst_path = f"{generator_dir}/flux_par.yaml"
    file_to_copy = f"{EXAMPLES_DIR}/flux/flux_par.yaml"

    write_example(file_to_copy, generator_dir)
    assert os.path.exists(dst_path)


def test_list_examples():
    """Test the `list_examples` function to see if it gives us all of the examples that we want."""
    expected_headers = ["name", "description"]
    expected_rows = [
        ["openfoam_wf_no_docker", "A parameter study that includes initializing, running,\n" \
                                  "post-processing, collecting, learning and vizualizing OpenFOAM runs\n" \
                                  "without using docker."],
        ["optimization_basic", "Design Optimization Template\n" \
                               "To use,\n" \
                               "1. Specify the first three variables here (N_DIMS, TEST_FUNCTION, DEBUG)\n" \
                               "2. Run the template_config file in current directory using `python template_config.py`\n" \
                               "3. Merlin run as usual (merlin run optimization.yaml)\n" \
                               "* MAX_ITER and the N_SAMPLES options use default values unless using DEBUG mode\n" \
                               "* BOUNDS_X and UNCERTS_X are configured using the template_config.py scripts"],
        ["feature_demo", "Run 10 hello worlds."],
        ["flux_local", "Run a scan through Merlin/Maestro"],
        ["flux_par", "A simple ensemble of parallel MPI jobs run by flux."],
        ["flux_par_restart", "A simple ensemble of parallel MPI jobs run by flux."],
        ["paper_flux", "Use flux to run single core MPI jobs and record timings."],
        ["lsf_par", "A simple ensemble of parallel MPI jobs run by lsf (jsrun)."],
        ["lsf_par_srun", "A simple ensemble of parallel MPI jobs run by lsf using the srun wrapper (srun)."],
        ["restart", "A simple ensemble of with restarts."],
        ["restart_delay", "A simple ensemble of with restart delay times."],
        ["simple_chain", "test to see that chains are not run in parallel"],
        ["slurm_par", "A simple ensemble of parallel MPI jobs run by slurm (srun)."],
        ["slurm_par_restart", "A simple ensemble of parallel MPI jobs run by slurm (srun)."],
        ["remote_feature_demo", "Run 10 hello worlds."],
        ["hello", "a very simple merlin workflow"],
        ["hello_samples", "a very simple merlin workflow, with samples"],
        ["hpc_demo", "Demo running a workflow on HPC machines"],
        ["openfoam_wf", "A parameter study that includes initializing, running,\n" \
                        "post-processing, collecting, learning and visualizing OpenFOAM runs\n" \
                        "using docker."],
        ["openfoam_wf_singularity", "A parameter study that includes initializing, running,\n" \
                                    "post-processing, collecting, learning and visualizing OpenFOAM runs\n" \
                                    "using singularity."],
        ["null_chain", "Run N_SAMPLES steps of TIME seconds each at CONC concurrency.\n" \
                       "May be used to measure overhead in merlin.\n" \
                       "Iterates thru a chain of workflows."],
        ["null_spec", "run N_SAMPLES null steps at CONC concurrency for TIME seconds each. May be used to measure overhead in merlin."],
        ["iterative_demo", "Demo of a workflow with self driven iteration/looping"],
    ]
    expected = "\n" + tabulate(expected_rows, expected_headers) + "\n"
    actual = list_examples()
    assert actual == expected


def test_setup_example_invalid_name():
    """
    Test the `setup_example` function with an invalid example name.
    This should just return None.
    """
    assert setup_example("invalid_example_name", None) is None


def test_setup_example_no_outdir(temp_output_dir: str):
    """
    Test the `setup_example` function with an invalid example name.
    This should create a directory with the example name (in this case hello)
    and copy all of the example contents to this folder.
    We'll create a directory specifically for this test and move into it so that
    the `setup_example` function creates the hello/ subdirectory in a directory with
    the name of this test (setup_no_outdir).

    :param temp_output_dir: The path to the temporary output directory we'll be using for this test run
    """
    cwd = os.getcwd()

    # Create the temp path to store this setup and move into that directory
    generator_dir = EXAMPLES_GENERATOR_DIR.format(temp_output_dir=temp_output_dir)
    create_dir(generator_dir)
    setup_example_dir = os.path.join(generator_dir, "setup_no_outdir")
    create_dir(setup_example_dir)
    os.chdir(setup_example_dir)

    # This should still work and return to us the name of the example
    try:
        assert setup_example("hello", None) == "hello"
    except AssertionError as exc:
        os.chdir(cwd)
        raise AssertionError from exc

    # All files from this example should be written to a directory with the example name
    full_output_path = os.path.join(setup_example_dir, "hello")
    expected_files = [
        os.path.join(full_output_path, "hello_samples.yaml"),
        os.path.join(full_output_path, "hello.yaml"),
        os.path.join(full_output_path, "my_hello.yaml"),
        os.path.join(full_output_path, "requirements.txt"),
        os.path.join(full_output_path, "make_samples.py"),
    ]
    try:
        for file in expected_files:
            assert os.path.exists(file)
    except AssertionError as exc:
        os.chdir(cwd)
        raise AssertionError from exc


def test_setup_example_outdir_exists(temp_output_dir: str):
    """
    Test the `setup_example` function with an output directory that already exists.
    This should just return None.

    :param temp_output_dir: The path to the temporary output directory we'll be using for this test run
    """
    generator_dir = EXAMPLES_GENERATOR_DIR.format(temp_output_dir=temp_output_dir)
    create_dir(generator_dir)

    assert setup_example("hello", generator_dir) is None


#####################################
# Tests for setting up each example #
#####################################


def run_setup_example(temp_output_dir: str, example_name: str, example_files: List[str], expected_return: str):
    """
    Helper function to run tests for the `setup_example` function.

    :param temp_output_dir: The path to the temporary output directory we'll be using for this test run
    :param example_name: The name of the example to setup
    :param example_files: A list of filenames that should be copied by setup_example
    :param expected_return: The expected return value from `setup_example`
    """
    # Create the temp path to store this setup
    generator_dir = EXAMPLES_GENERATOR_DIR.format(temp_output_dir=temp_output_dir)
    create_dir(generator_dir)
    setup_example_dir = os.path.join(generator_dir, f"setup_{example_name}")

    # Ensure that the example name is returned
    actual = setup_example(example_name, setup_example_dir)
    assert actual == expected_return

    # Ensure all of the files that should've been copied were copied
    expected_files = [os.path.join(setup_example_dir, expected_file) for expected_file in example_files]
    for file in expected_files:
        assert os.path.exists(file)


def test_setup_example_feature_demo(temp_output_dir: str):
    """
    Test the `setup_example` function for the feature_demo example.

    :param temp_output_dir: The path to the temporary output directory we'll be using for this test run
    """
    example_name = "feature_demo"
    example_files = [
        ".gitignore",
        "feature_demo.yaml",
        "requirements.txt",
        "scripts/features.json",
        "scripts/hello_world.py",
        "scripts/pgen.py",
    ]

    run_setup_example(temp_output_dir, example_name, example_files, example_name)


def test_setup_example_flux(temp_output_dir: str):
    """
    Test the `setup_example` function for the flux example.

    :param temp_output_dir: The path to the temporary output directory we'll be using for this test run
    """
    example_files = [
        "flux_local.yaml",
        "flux_par_restart.yaml",
        "flux_par.yaml",
        "paper.yaml",
        "requirements.txt",
        "scripts/flux_info.py",
        "scripts/hello_sleep.c",
        "scripts/hello.c",
        "scripts/make_samples.py",
        "scripts/paper_workers.sbatch",
        "scripts/test_workers.sbatch",
        "scripts/workers.sbatch",
        "scripts/workers.bsub",
    ]

    run_setup_example(temp_output_dir, "flux_local", example_files, "flux")


def test_setup_example_lsf(temp_output_dir: str):
    """
    Test the `setup_example` function for the lsf example.

    :param temp_output_dir: The path to the temporary output directory we'll be using for this test run
    """

    # TODO should there be a workers.bsub for this example?
    example_files = [
        "lsf_par_srun.yaml",
        "lsf_par.yaml",
        "scripts/hello.c",
        "scripts/make_samples.py",
    ]

    run_setup_example(temp_output_dir, "lsf_par", example_files, "lsf")


def test_setup_example_slurm(temp_output_dir: str):
    """
    Test the `setup_example` function for the slurm example.

    :param temp_output_dir: The path to the temporary output directory we'll be using for this test run
    """
    example_files = [
        "slurm_par.yaml",
        "slurm_par_restart.yaml",
        "requirements.txt",
        "scripts/hello.c",
        "scripts/make_samples.py",
        "scripts/test_workers.sbatch",
        "scripts/workers.sbatch",
    ]

    run_setup_example(temp_output_dir, "slurm_par", example_files, "slurm")


def test_setup_example_hello(temp_output_dir: str):
    """
    Test the `setup_example` function for the hello example.

    :param temp_output_dir: The path to the temporary output directory we'll be using for this test run
    """
    example_name = "hello"
    example_files = [
        "hello_samples.yaml",
        "hello.yaml",
        "my_hello.yaml",
        "requirements.txt",
        "make_samples.py",
    ]

    run_setup_example(temp_output_dir, example_name, example_files, example_name)


def test_setup_example_hpc(temp_output_dir: str):
    """
    Test the `setup_example` function for the hpc_demo example.

    :param temp_output_dir: The path to the temporary output directory we'll be using for this test run
    """
    example_name = "hpc_demo"
    example_files = [
        "hpc_demo.yaml",
        "cumulative_sample_processor.py",
        "faker_sample.py",
        "sample_collector.py",
        "sample_processor.py",
        "requirements.txt",
    ]

    run_setup_example(temp_output_dir, example_name, example_files, example_name)


def test_setup_example_iterative(temp_output_dir: str):
    """
    Test the `setup_example` function for the iterative_demo example.

    :param temp_output_dir: The path to the temporary output directory we'll be using for this test run
    """
    example_name = "iterative_demo"
    example_files = [
        "iterative_demo.yaml",
        "cumulative_sample_processor.py",
        "faker_sample.py",
        "sample_collector.py",
        "sample_processor.py",
        "requirements.txt",
    ]

    run_setup_example(temp_output_dir, example_name, example_files, example_name)


def test_setup_example_null(temp_output_dir: str):
    """
    Test the `setup_example` function for the null_spec example.

    :param temp_output_dir: The path to the temporary output directory we'll be using for this test run
    """
    example_name = "null_spec"
    example_files = [
        "null_spec.yaml",
        "null_chain.yaml",
        ".gitignore",
        "Makefile",
        "requirements.txt",
        "scripts/aggregate_chain_output.sh",
        "scripts/aggregate_output.sh",
        "scripts/check_completion.sh",
        "scripts/kill_all.sh",
        "scripts/launch_chain_job.py",
        "scripts/launch_jobs.py",
        "scripts/make_samples.py",
        "scripts/read_output_chain.py",
        "scripts/read_output.py",
        "scripts/search.sh",
        "scripts/submit_chain.sbatch",
        "scripts/submit.sbatch",
    ]

    run_setup_example(temp_output_dir, example_name, example_files, example_name)


def test_setup_example_openfoam(temp_output_dir: str):
    """
    Test the `setup_example` function for the openfoam_wf example.

    :param temp_output_dir: The path to the temporary output directory we'll be using for this test run
    """
    example_name = "openfoam_wf"
    example_files = [
        "openfoam_wf.yaml",
        "openfoam_wf_template.yaml",
        "README.md",
        "requirements.txt",
        "scripts/make_samples.py",
        "scripts/blockMesh_template.txt",
        "scripts/cavity_setup.sh",
        "scripts/combine_outputs.py",
        "scripts/learn.py",
        "scripts/mesh_param_script.py",
        "scripts/run_openfoam",
    ]

    run_setup_example(temp_output_dir, example_name, example_files, example_name)


def test_setup_example_openfoam_no_docker(temp_output_dir: str):
    """
    Test the `setup_example` function for the openfoam_wf_no_docker example.

    :param temp_output_dir: The path to the temporary output directory we'll be using for this test run
    """
    example_name = "openfoam_wf_no_docker"
    example_files = [
        "openfoam_wf_no_docker.yaml",
        "openfoam_wf_no_docker_template.yaml",
        "requirements.txt",
        "scripts/make_samples.py",
        "scripts/blockMesh_template.txt",
        "scripts/cavity_setup.sh",
        "scripts/combine_outputs.py",
        "scripts/learn.py",
        "scripts/mesh_param_script.py",
        "scripts/run_openfoam",
    ]

    run_setup_example(temp_output_dir, example_name, example_files, example_name)


def test_setup_example_openfoam_singularity(temp_output_dir: str):
    """
    Test the `setup_example` function for the openfoam_wf_singularity example.

    :param temp_output_dir: The path to the temporary output directory we'll be using for this test run
    """
    example_name = "openfoam_wf_singularity"
    example_files = [
        "openfoam_wf_singularity.yaml",
        "requirements.txt",
        "scripts/make_samples.py",
        "scripts/blockMesh_template.txt",
        "scripts/cavity_setup.sh",
        "scripts/combine_outputs.py",
        "scripts/learn.py",
        "scripts/mesh_param_script.py",
        "scripts/run_openfoam",
    ]

    run_setup_example(temp_output_dir, example_name, example_files, example_name)


def test_setup_example_optimization(temp_output_dir: str):
    """
    Test the `setup_example` function for the optimization example.

    :param temp_output_dir: The path to the temporary output directory we'll be using for this test run
    """
    example_files = [
        "optimization_basic.yaml",
        "requirements.txt",
        "template_config.py",
        "template_optimization.temp",
        "scripts/collector.py",
        "scripts/optimizer.py",
        "scripts/test_functions.py",
        "scripts/visualizer.py",
    ]

    run_setup_example(temp_output_dir, "optimization_basic", example_files, "optimization")


def test_setup_example_remote_feature_demo(temp_output_dir: str):
    """
    Test the `setup_example` function for the remote_feature_demo example.

    :param temp_output_dir: The path to the temporary output directory we'll be using for this test run
    """
    example_name = "remote_feature_demo"
    example_files = [
        ".gitignore",
        "remote_feature_demo.yaml",
        "requirements.txt",
        "scripts/features.json",
        "scripts/hello_world.py",
        "scripts/pgen.py",
    ]

    run_setup_example(temp_output_dir, example_name, example_files, example_name)


def test_setup_example_restart(temp_output_dir: str):
    """
    Test the `setup_example` function for the restart example.

    :param temp_output_dir: The path to the temporary output directory we'll be using for this test run
    """
    example_name = "restart"
    example_files = [
        "restart.yaml",
        "scripts/make_samples.py"
    ]

    run_setup_example(temp_output_dir, example_name, example_files, example_name)


def test_setup_example_restart_delay(temp_output_dir: str):
    """
    Test the `setup_example` function for the restart_delay example.

    :param temp_output_dir: The path to the temporary output directory we'll be using for this test run
    """
    example_name = "restart_delay"
    example_files = [
        "restart_delay.yaml",
        "scripts/make_samples.py"
    ]

    run_setup_example(temp_output_dir, example_name, example_files, example_name)


def test_setup_example_simple_chain(temp_output_dir: str):
    """
    Test the `setup_example` function for the simple_chain example.

    :param temp_output_dir: The path to the temporary output directory we'll be using for this test run
    """

    # Create the temp path to store this setup
    generator_dir = EXAMPLES_GENERATOR_DIR.format(temp_output_dir=temp_output_dir)
    create_dir(generator_dir)
    output_file = os.path.join(generator_dir, "simple_chain.yaml")

    # Ensure that the example name is returned
    actual = setup_example("simple_chain", output_file)
    assert actual == "simple_chain"
    assert os.path.exists(output_file)
