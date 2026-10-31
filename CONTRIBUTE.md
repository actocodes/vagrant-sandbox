# Contributing

Thank you for helping improve `vagrant-sandbox`. This guide is for people
developing the package or contributing changes to the repository. End-user
installation and usage instructions are in [README.md](./README.md).

## Development setup

Requirements: Python 3.11 or newer. From a checkout, create and activate a
virtual environment, then install the project:

```console
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -e .
```

Vagrant and a provider are only needed to manually test a generated environment, the unit tests do not start a VM.

## Tests and package checks

Run the test suite:

```console
python -m unittest discover -s tests -v
```

Build and validate the release distributions:

```console
python -m pip install --upgrade build twine
python -m build
python -m twine check dist/*
```

The GitHub Actions CI workflow runs unit tests on Python 3.11 and 3.14 and
builds/checks distributions.

## Project structure

- `src/vagrant_sandbox/cli.py` defines the command-line interface.
- `src/vagrant_sandbox/settings.py` loads, merges, and validates settings.
- `src/vagrant_sandbox/generator.py` renders the Vagrantfile, copies
  provisioning scripts, and invokes Vagrant.
- `src/vagrant_sandbox/templates/` contains the Vagrantfile template.
- `src/vagrant_sandbox/profiles/` contains the built-in shell scripts.
- `tests/` contains the standard-library `unittest` suite.
- `.github/workflows/` contains CI and PyPI publishing workflows.

The `src/` tree is the source of truth. `build/` and `dist/` are generated artifacts do not edit them by hand.

## Change guidelines

- Keep changes focused and preserve existing behavior unless a behavior change
  is part of the task.
- Add or update tests when changing CLI, settings, generation, or provisioning
  behavior.
- Keep end-user documentation in `README.md`, contributor and release process
  documentation here, and coding-agent-specific instructions in `AGENTS.md`.
- Do not add a dependency for functionality already available in the Python
  standard library without a clear need.
- Never commit credentials, private keys, or other secrets.
