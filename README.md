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
- A usable provider for your operating system:
  - Windows: Hyper-V; run the command from an elevated Administrator shell.
  - Linux: vagrant-libvirt with QEMU/KVM, libvirt, and access through the `libvirt` group. VirtualBox is used as a fallback if libvirt is not ready.
  - macOS: VirtualBox. Apple Silicon requires an arm64 box build. 
  - VMware Desktop and Parallels remain available when explicitly selected.

Vagrant and its providers are installed separately, installing this Python package does not install them. On Linux, install the distribution's QEMU/KVM and libvirt packages, install the `vagrant-libvirt` Vagrant plugin, enable the libvirt service, and add your account to the `libvirt` group before logging back in. The generated default box is `generic/ubuntu2204`.

On Linux, install the plugin with `vagrant plugin install vagrant-libvirt`.

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
| `--vm-ip ADDRESS` | Set the static private IPv4 address (used by providers that require it). |
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

# Choose a provider and machine settings. Static-IP providers need an address.
vagrant-sandbox create --provider virtualbox --vm-name web-dev --vm-ip 192.168.56.21 --cpus 4 --memory 4096

# Choose profiles and add two custom provisioning scripts.
vagrant-sandbox create --profile python --profile nodejs --provision ./scripts/install-tools.sh --provision ./scripts/configure-shell.sh

# Read shared settings from JSON, override selected values, then start.
vagrant-sandbox create --config sandbox.json --vm-name web-dev --provider virtualbox

# Replace generated files after changing settings or profiles.
vagrant-sandbox create --config sandbox.json --force
```

The provider is passed to the initial `vagrant up` and is not saved as a provider selection in the generated `Vagrantfile`. When starting a generated project later, the Vagrantfile sets `VAGRANT_DEFAULT_PROVIDER` based on `Vagrant::Util::Platform`, you can override that choice with
`vagrant up --provider NAME`. The CLI checks Linux libvirt prerequisites and announces when it uses the VirtualBox fallback, a later direct `vagrant up` uses the platform default and therefore requires that provider to be ready.

## Settings and configuration

Settings can come from defaults, a JSON config file, command-line options, and
interactive prompts:

1. Built-in defaults are used for unspecified values.
2. Config values override defaults.
3. Command-line options override config values.
4. In an interactive terminal, prompts are shown for values not explicitly set on the command line. Press Enter to keep the displayed value, entering a blank provider selects the automatic host-OS default.

Use `--non-interactive` to skip prompts, which is useful in scripts and CI.

Example `sandbox.json`:

```json
{
  "vm_name": "web-dev",
  "cpus": 4,
  "memory": 4096,
  "box": "generic/ubuntu2204",
  "provider": "virtualbox",
  "profiles": ["base", "docker", "nodejs", "python"],
  "custom_scripts": ["scripts/install-tools.sh"]
}
```

All config keys are optional. The defaults are:

| Setting | Default |
| --- | --- |
| `vm_name` | `sandbox` |
| `vm_ip` | `192.168.56.10` (static-IP providers only) |
| `cpus` | `2` |
| `memory` | `2048` MB |
| `box` | `generic/ubuntu2204` |
| `provider` | Automatically selected for the host OS |
| `profiles` | `["base"]` |
| `custom_scripts` | `[]` |

The VM name must be 1–63 letters, digits, hyphens, or underscores, starting with a letter or digit. For providers that use a static private network
(including libvirt and VirtualBox), the IP must be a private IPv4 address in `10/8`, `172.16/12`, or `192.168/16`, choose a distinct address for each VM on the same host. Hyper-V uses the Default Switch and obtains its address dynamically, so no IP prompt is shown. CPU count must be between 1 and 256, and memory between 512 and 1,048,576 MB. The box must be a non-empty, single-line name. Provider names may contain letters, digits, underscores, and hyphens.

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

The provider is selected from the host OS: Hyper-V on Windows, libvirt on Linux (with VirtualBox fallback when libvirt prerequisites are unavailable), and VirtualBox on macOS (Intel and Apple Silicon). On Apple Silicon the box must have an arm64 build. VMware Desktop and Parallels remain available when explicitly selected. A provider explicitly requested by the user is never silently changed. The CLI uses an explicit provider flag, so missing or unavailable providers fail with Vagrant's provider error rather than silently switching to another hypervisor. Hyper-V startup is rejected unless the process is elevated. On Linux, the tool checks for running guests on the other hypervisor and refuses to start VirtualBox while KVM guests are running, or vice versa.

Libvirt and static-IP providers use a private network, Hyper-V uses its Default Switch with a dynamically assigned address. The generated environment does not forward application ports. Synced folders are disabled, SSH agent and X11 forwarding are disabled, clipboard and drag-and-drop are disabled, and USB device auto-connection is disabled where supported. Clone code inside `~/workspace` in the guest rather than expecting host files to appear there.

All providers receive a systemd-resolved DNS configuration to avoid DNSSEC failures, followed by a provisioning smoke test that resolves
`mirrors.edge.kernel.org`. Provisioning stops with an error if DNS is not working.

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
- **The private IP is already in use:** for a static-IP provider, choose another unused private IPv4 address with `--vm-ip`.
- **A custom script is reported missing:** check the path base. Config paths
  are relative to the config file, `--provision` paths are relative to the
  command's current directory.
- **Generated files already exist:** use a new `--directory` or pass `--force`
  after confirming you want to replace those files.
- **The guest cannot see host project files:** this is intentional. Clone or
  copy repositories into the guest's `~/workspace`.
