# Design Optimization Example

The design optimization example was created as a way to show how Merlin can be utilized for machine-learning based design optimization workflows.

You can obtain all of the files necessary to run this example with:

```bash
merlin example optimization_basic
```

Once this command has been executed, you should have a folder called `optimization` with the following files:

```bash
optimization/
├── optimization_basic.yaml
├── requirements.txt
├── scripts
│   ├── collector.py
│   ├── optimizer.py
│   ├── test_functions.py
│   └── visualizer.py
├── template_config.py
└── template_optimization.temp
```

These files will each be discussed in more detail in their own sections but can be summarized as so:

- `optimization_basic.yaml`: A basic Merlin spec file to run this example
- `requirements.txt`: A requirements file listing third party libraries that need to be installed with pip to run this example
- `scripts/collector.py`:
- `scripts/optimizer.py`:
- `scripts/test_functions.py`:
- `scripts/visualizer.py`:
- `template_config.py`: A script to create a custom optimization Merlin spec file
- `template_optimization.temp`: The temp file used for custom spec configuration