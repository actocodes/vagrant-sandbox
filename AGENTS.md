# Instructions for AI coding agents

These instructions apply to coding agents working in this repository.

## Repository map

- Application source of truth: `src/vagrant_sandbox/`
- Tests: `tests/` (`unittest`)
- End-user documentation: `README.md`
- Contributor and release instructions: `CONTRIBUTE.md`
- Agent guidance: `AGENTS.md`
- CI and publishing: `.github/workflows/`
- Built-in provisioning scripts: `src/vagrant_sandbox/profiles/`
- Vagrantfile template: `src/vagrant_sandbox/templates/`

Do not edit generated copies under `build/` or `dist/` by hand. Update source
files and regenerate artifacts only when needed.

## Working practices

- Read the affected implementation and tests before changing behavior.
- Prefer small, direct changes that follow the existing Python and shell
  patterns. Avoid unrelated refactors.
- Preserve validation, error reporting, configuration precedence, and generated
  output unless the task explicitly changes them.
- Add or update focused tests for behavior changes. Run
  `python -m unittest discover -s tests -v` for relevant changes.
- For packaging or release changes, run `python -m build` and
  `python -m twine check dist/*` when the required tools are available.
- Keep end-user instructions in `README.md`, contributor instructions in
  `CONTRIBUTE.md`, and agent-specific instructions in this file.
- Keep all `.sh` files under `src/vagrant_sandbox/profiles/` LF-terminated, `.gitattributes` declares this requirement.
- Do not commit generated secrets, credentials, or private keys.

## Product-specific details

- The console command is registered in `pyproject.toml` as
  `vagrant_sandbox.cli:main`.
- `settings.py` defines defaults and merges config, CLI, and interactive
  settings. Config-file custom-script paths are relative to the config file, CLI and prompted script paths are resolved from the current working directory.
- `base` is always included in selected provisioning profiles.
- `generator.py` uses the packaged template and profile scripts to create a project in the selected output directory. Provider selection is passed to the initial `vagrant up`, it is not embedded as a selected provider in the generated Vagrantfile.
- The `docker` profile installs Docker Engine inside the guest. It is not a Vagrant Docker provider.
- Custom provisioning scripts run inside the guest as Vagrant shell provisioners, treat them as executable user-supplied code and preserve validation and error reporting.
