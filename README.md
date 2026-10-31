# Vagrant Sandbox

`vagrant-sandbox` generates an isolated Ubuntu Vagrant environment, copies the selected provisioning scripts into the project, and can start the VM immediately.

## Requirements

- Python 3.11 or newer
- Vagrant installed and available on `PATH`
- A Vagrant provider such as VirtualBox, VMware, or Parallels

## Install and run

Install the command with `pipx`:

```console
pipx install vagrant-sandbox
vagrant-sandbox create
```

For a one-off run without a persistent installation:

```console
pipx run vagrant-sandbox create
```

For local development from a checkout:

```console
python -m pip install .
vagrant-sandbox create
```

`create` prompts for VM settings in an interactive terminal, writes a `Vagrantfile` and `.vagrant-sandbox/provision/` scripts in the current directory, then runs `vagrant up`. To create the files without starting the VM:

```console
vagrant-sandbox create --no-up
```

Use `--directory` to choose another output directory. Existing generated files are never replaced unless `--force` is provided.

Choose a distinct private IP for each VM that runs on the same host.

## Customize

Configuration precedence is command-line options over JSON config values over built-in defaults. An example config:

```json
{
  "vm_name": "web-dev",
  "vm_ip": "192.168.56.20",
  "cpus": 4,
  "memory": 4096,
  "box": "bento/ubuntu-24.04",
  "provider": "virtualbox",
  "profiles": ["base", "docker", "nodejs"],
  "custom_scripts": ["scripts/install-tools.sh"]
}
```

Custom script paths in a config file are relative to that config file. Scripts are copied into the generated project and run as privileged Vagrant shell provisioners, after the built-in profiles. Only use scripts you trust.

```console
vagrant-sandbox create --config sandbox.json --vm-name web-dev --cpus 4
vagrant-sandbox create --profile python --profile docker --provision ./scripts/extra.sh
vagrant-sandbox profiles
```

Supported profiles are `base`, `docker`, `nodejs`, and `python`. The `base` profile is always included. `--profile` can be repeated to choose profiles, when omitted, config profiles are used, then the default `base`.

The generated VM does not share the project directory with the host and disables SSH agent forwarding. It uses a host-only private network and does not forward application ports to localhost. Run `vagrant destroy` from the generated project directory to remove the VM.
