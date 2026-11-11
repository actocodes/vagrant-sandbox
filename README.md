# Vagrant Sandbox

`vagrant-sandbox` creates an Ubuntu development environment managed by
[Vagrant](https://developer.hashicorp.com/vagrant). It generates a `Vagrantfile`,
copies the selected setup scripts into your project, and can start the
environment immediately. Use it to get a repeatable development machine without
sharing your host project directory with the guest.

## Requirements

- Python 3.11 or newer
- [Vagrant](https://developer.hashicorp.com/vagrant/install) installed and available on `PATH`
- A Vagrant version with built-in trigger support
- A Vagrant provider installed and usable by Vagrant:
  - VirtualBox (`virtualbox`)
  - VMware (`vmware_desktop`)
  - Parallels (`parallels`)

Vagrant and its providers are installed separately, installing this Python package does not install them. The selected box must support the provider you intend to use.

## Install

Install the command with [pipx](https://pipx.pypa.io/):

```console
pipx install vagrant-sandbox
vagrant-sandbox --help
```

Run once without a persistent pipx installation:

```console
pipx run vagrant-sandbox --help
pipx run vagrant-sandbox create
```

On a Windows setup that invokes pipx as a Python module:

```console
python -m pipx run vagrant-sandbox create
```

## Quick start

From the directory where you want the generated Vagrant project:

```console
vagrant-sandbox create
```

In an interactive terminal, the command prompts for VM settings. Accept the displayed defaults by pressing Enter. It writes:

- `Vagrantfile`
- `.vagrant-sandbox/provision/` with the selected built-in and custom scripts

It then runs `vagrant up` unless `--no-up` is specified. After the machine is running, connect with `vagrant ssh`. The default setup creates `~/workspace` inside the guest, clone your repositories there.

After `vagrant up` or `vagrant reload`, the generated Vagrantfile updates a managed `sandbox-<VM_NAME>` host block at the beginning of your user SSH config using Vagrant's current SSH connection details. To connect VS Code, install the Remote - SSH extension and connect to that host alias. For the default VM name, the alias is `sandbox-sandbox`. The trigger changes only its own marked block and preserves the rest of `~/.ssh/config`.

## Commands

```console
vagrant-sandbox --help
vagrant-sandbox create --help
vagrant-sandbox profiles
```

`profiles` lists the built-in provisioning profiles. `create` supports:

| Option | Purpose |
| --- | --- |
| `--config FILE` | Read settings from a JSON configuration file. |
| `--directory DIR` | Generate the project in `DIR` instead of the current directory. |
| `--vm-name NAME` | Set the VM hostname/name. |
| `--vm-ip ADDRESS` | Set the private host-only IPv4 address. |
| `--cpus COUNT` | Set the CPU count. |
| `--memory MB` | Set memory in megabytes. |
| `--box BOX` | Select a Vagrant box. |
| `--provider NAME` | Select a Vagrant provider for this `vagrant up`. |
| `--profile NAME` | Select a built-in profile; repeat for multiple profiles. |
| `--provision FILE` | Add a custom shell script; repeat for multiple scripts. |
| `--no-up` | Generate files without starting Vagrant. |
| `--non-interactive` | Do not prompt; use config values and defaults. |
| `--force` | Replace generated files that already exist. |

Examples:

```console
# Generate in the current directory, prompt if interactive, and start Vagrant.
vagrant-sandbox create

# Run non-interactively with defaults, generate files and start the default provider.
vagrant-sandbox create --non-interactive

# Generate files only, in another directory.
vagrant-sandbox create --directory ../web-sandbox --no-up

# Choose a provider and machine settings.
vagrant-sandbox create --provider virtualbox --vm-name web-dev --vm-ip 192.168.56.21 --cpus 4 --memory 4096

# Choose profiles and add two custom provisioning scripts.
vagrant-sandbox create --profile python --profile nodejs --provision ./scripts/install-tools.sh --provision ./scripts/configure-shell.sh

# Read shared settings from JSON, override selected values, then start.
vagrant-sandbox create --config sandbox.json --vm-name web-dev --provider virtualbox

# Replace generated files after changing settings or profiles.
vagrant-sandbox create --config sandbox.json --force
```

If you use `--no-up` with `--provider`, the provider is not saved in the
generated `Vagrantfile`. When starting it later, select the provider explicitly,
for example `vagrant up --provider virtualbox`, or omit the option to let
Vagrant choose its default provider.

## Settings and configuration

Settings can come from defaults, a JSON config file, command-line options, and
interactive prompts:

1. Built-in defaults are used for unspecified values.
2. Config values override defaults.
3. Command-line options override config values.
4. In an interactive terminal, prompts are shown for values not explicitly set
   on the command line. Press Enter to keep the displayed value, except a blank
   provider clears a provider from config and lets Vagrant choose.

Use `--non-interactive` to skip prompts, which is useful in scripts and CI.

Example `sandbox.json`:

```json
{
  "vm_name": "web-dev",
  "vm_ip": "192.168.56.21",
  "cpus": 4,
  "memory": 4096,
  "box": "bento/ubuntu-24.04",
  "provider": "virtualbox",
  "profiles": ["base", "docker", "nodejs", "python"],
  "custom_scripts": ["scripts/install-tools.sh"]
}
```

All config keys are optional. The defaults are:

| Setting | Default |
| --- | --- |
| `vm_name` | `sandbox` |
| `vm_ip` | `192.168.56.10` |
| `cpus` | `2` |
| `memory` | `2048` MB |
| `box` | `bento/ubuntu-24.04` |
| `provider` | Vagrant's default provider |
| `profiles` | `["base"]` |
| `custom_scripts` | `[]` |

The VM name must be 1–63 letters, digits, hyphens, or underscores, starting
with a letter or digit. The IP must be a private IPv4 address in `10/8`,
`172.16/12`, or `192.168/16`; choose a distinct address for each VM on the same
host. CPU count must be between 1 and 256, and memory between 512 and 1,048,576
MB. The box must be a non-empty, single-line name. Provider names may contain
letters, digits, underscores, and hyphens.

Config paths for `custom_scripts` are resolved relative to the JSON config
file. Paths supplied with `--provision` or at an interactive prompt are
resolved relative to the current working directory. All custom scripts must
exist before generation.

## Provisioning profiles

The `base` profile is always included, even when omitted from config or CLI
selection. If no profiles are selected, only `base` is installed. Profiles are
run in order after the base profile, followed by user setup and then custom
scripts.

| Profile | Installs or configures |
| --- | --- |
| `base` | Build tools, Git, curl/wget, common command-line utilities, UTC timezone, and base packages. |
| `docker` | Docker Engine inside the guest and adds the `vagrant` user to the `docker` group. This is not a Docker Vagrant provider. |
| `nodejs` | Node.js LTS. |
| `python` | Python 3, pip, venv, pipx, uv, and uvx. |

Select one or combine profiles:

```console
vagrant-sandbox create --profile python
vagrant-sandbox create --profile docker --profile nodejs
```

The CLI profile options replace the profile list from config. Custom
`--provision` scripts are appended to config `custom_scripts`. Provisioning
scripts are copied into `.vagrant-sandbox/provision/` and run by Vagrant as
shell provisioners after built-in profiles. Only use custom scripts you trust,
they can run privileged commands inside the guest.

## Provider and networking behavior

The generated Vagrantfile includes configuration for VirtualBox, VMware
Desktop, and Parallels. `--provider` passes the selected provider to the initial
`vagrant up`, it does not rewrite the Vagrantfile. If no provider is selected,
Vagrant chooses its default/available provider. Provider-specific options only
apply when that provider is used.

The generated environment uses a private host-only network at the configured
IP. It does not forward application ports to localhost. The project directory
is not shared with the guest, and SSH agent and X11 forwarding are disabled.
Clone code inside `~/workspace` in the guest rather than expecting host files
to appear there.

After the VM starts, Vagrant adds its configured name and private IP to the
host's hosts file so the VM can be reached by name. This requires administrator
approval on Windows or `sudo` access on Linux/macOS. The entry is updated on
subsequent starts and removed by `vagrant destroy`; unrelated hosts-file
content is preserved. If the name already has an unmanaged hosts entry,
Vagrant reports a conflict rather than changing it.

## Existing generated files and lifecycle

The tool refuses to overwrite a generated `Vagrantfile` or selected
provisioning files unless `--force` is provided. `--force` replaces files
selected for the current generation, it does not remove obsolete provisioning
files from earlier configurations.

Run Vagrant commands from the generated project directory:

```console
vagrant up
vagrant ssh
vagrant halt
vagrant status
vagrant destroy
```

Use `vagrant destroy` to remove the VM. The generated project files remain on
the host and can be reused to create it again.

## Troubleshooting

- **Vagrant is not found:** install Vagrant and ensure its executable is on
  `PATH`.
- **Provider is unavailable:** install/configure the provider and ensure the
  selected box supports it.
- **The private IP is already in use:** choose another unused private IPv4
  address with `--vm-ip`.
- **A custom script is reported missing:** check the path base. Config paths
  are relative to the config file, `--provision` paths are relative to the
  command's current directory.
- **Generated files already exist:** use a new `--directory` or pass `--force`
  after confirming you want to replace those files.
- **The guest cannot see host project files:** this is intentional. Clone or
  copy repositories into the guest's `~/workspace`.
