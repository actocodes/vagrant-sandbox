import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

from .settings import Settings


PACKAGE_DIR = Path(__file__).parent
TEMPLATE_PATH = PACKAGE_DIR / "templates" / "Vagrantfile.template"
PROFILES_DIR = PACKAGE_DIR / "profiles"
PROVISION_DIR = Path(".vagrant-sandbox") / "provision"
USER_SETUP_SCRIPT = "user-setup.sh"


def render_vagrantfile(settings: Settings) -> str:
    blocks = [
        _provision_block(f"profile-{profile}", PROVISION_DIR / f"{profile}.sh")
        for profile in settings.profiles
    ]
    blocks.append(
        _provision_block(
            "user-setup",
            PROVISION_DIR / USER_SETUP_SCRIPT,
            privileged=False,
        )
    )
    blocks.extend(
        _provision_block(
            f"custom-{index + 1}",
            PROVISION_DIR / f"custom-{index + 1}-{script.name}",
        )
        for index, script in enumerate(settings.custom_scripts)
    )
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    replacements = {
        "@@VM_NAME@@": json.dumps(settings.vm_name),
        "@@VM_IP@@": json.dumps(settings.vm_ip),
        "@@VM_CPUS@@": str(settings.cpus),
        "@@VM_MEMORY@@": str(settings.memory),
        "@@BOX@@": json.dumps(settings.box),
        "@@PROVISIONERS@@": "\n".join(blocks),
    }
    for marker, value in replacements.items():
        template = template.replace(marker, value)
    return template


def generate_project(settings: Settings, output_dir: Path, force: bool = False) -> Path:
    output_dir = output_dir.resolve()
    vagrantfile = output_dir / "Vagrantfile"
    provision_dir = output_dir / PROVISION_DIR
    generated_paths = [vagrantfile]
    generated_paths.extend(
        provision_dir / f"{profile}.sh" for profile in settings.profiles
    )
    generated_paths.append(provision_dir / USER_SETUP_SCRIPT)
    generated_paths.extend(
        provision_dir / f"custom-{index + 1}-{script.name}"
        for index, script in enumerate(settings.custom_scripts)
    )
    existing = [path for path in generated_paths if path.exists()]
    if existing and not force:
        names = ", ".join(str(path.relative_to(output_dir)) for path in existing)
        raise FileExistsError(
            f"Generated file(s) already exist: {names}. Use --force to replace them."
        )

    provision_dir.mkdir(parents=True, exist_ok=True)
    for profile in settings.profiles:
        source = PROFILES_DIR / f"{profile}.sh"
        shutil.copyfile(source, provision_dir / f"{profile}.sh")
    shutil.copyfile(
        PROFILES_DIR / USER_SETUP_SCRIPT,
        provision_dir / USER_SETUP_SCRIPT,
    )
    for index, script in enumerate(settings.custom_scripts):
        shutil.copyfile(script, provision_dir / f"custom-{index + 1}-{script.name}")
    vagrantfile.write_text(render_vagrantfile(settings), encoding="utf-8", newline="\n")
    return vagrantfile


def start_vm(settings: Settings, output_dir: Path) -> int:
    provider = settings.provider
    if settings.provider_auto and provider == "libvirt":
        provider = _linux_provider()
    if provider == "hyperv" and os.name == "nt" and not _is_windows_admin():
        raise RuntimeError(
            "The Hyper-V provider requires an elevated Administrator shell. "
            "Open PowerShell as Administrator and run vagrant-sandbox again."
        )
    if _is_linux():
        _ensure_no_conflicting_linux_guests(provider)

    command = ["vagrant", "up"]
    command.extend(["--provider", provider])
    try:
        result = subprocess.run(command, cwd=output_dir, check=False)
    except FileNotFoundError as error:
        raise RuntimeError(
            "Vagrant was not found. Install Vagrant and ensure it is on PATH."
        ) from error
    return result.returncode


def _linux_provider() -> str:
    try:
        plugins = subprocess.run(
            ["vagrant", "plugin", "list"],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except FileNotFoundError as error:
        raise RuntimeError(
            "Vagrant was not found. Install Vagrant and ensure it is on PATH."
        ) from error
    except subprocess.TimeoutExpired as error:
        raise RuntimeError("Timed out checking installed Vagrant providers.") from error
    has_libvirt_plugin = (
        plugins.returncode == 0 and "vagrant-libvirt" in plugins.stdout
    )
    has_libvirt_group = False
    if (
        hasattr(os, "geteuid")
        and hasattr(os, "getgid")
        and hasattr(os, "getgroups")
    ):
        try:
            import grp

            libvirt_gid = grp.getgrnam("libvirt").gr_gid
            has_libvirt_group = (
                os.geteuid() == 0
                or libvirt_gid == os.getgid()
                or libvirt_gid in os.getgroups()
            )
        except (AttributeError, KeyError, OSError):
            pass
    if (
        has_libvirt_plugin
        and shutil.which("virsh")
        and Path("/dev/kvm").exists()
        and has_libvirt_group
    ):
        return "libvirt"
    if shutil.which("VBoxManage"):
        print(
            "Warning: libvirt is not ready; using the VirtualBox fallback.",
            file=sys.stderr,
        )
        return "virtualbox"
    raise RuntimeError(
        "No usable Linux provider was found. Install Vagrant with the "
        "vagrant-libvirt plugin, QEMU/KVM, and libvirt group access, or install "
        "VirtualBox as a fallback."
    )


def _is_windows_admin() -> bool:
    try:
        import ctypes

        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except (AttributeError, OSError):
        return False


def _is_linux() -> bool:
    return platform.system() == "Linux"


def _ensure_no_conflicting_linux_guests(provider: str) -> None:
    checks: list[tuple[str, list[str]]] = []
    if provider == "libvirt" and shutil.which("VBoxManage"):
        checks.append(("VirtualBox", ["VBoxManage", "list", "runningvms"]))
    elif provider == "virtualbox" and shutil.which("virsh"):
        for uri in ("qemu:///system", "qemu:///session"):
            checks.append(
                (f"KVM/libvirt ({uri})", ["virsh", "-c", uri, "list", "--name"])
            )
    for conflicting_provider, command in checks:
        _check_conflicting_linux_guests(conflicting_provider, command, provider)


def _check_conflicting_linux_guests(
    conflicting_provider: str, command: list[str], provider: str
) -> None:
    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise RuntimeError(
            f"Could not check for running {conflicting_provider} guests: {error}"
        ) from error
    if result.returncode:
        details = result.stderr.strip() or result.stdout.strip()
        message = (
            f"Could not check for running {conflicting_provider} guests "
            "before starting this VM."
        )
        if details:
            message += f" {details}"
        raise RuntimeError(message)
    if result.stdout.strip():
        raise RuntimeError(
            f"Stop all running {conflicting_provider} guests before starting "
            f"a {provider} VM; VirtualBox and KVM must not run together."
        )


def _provision_block(name: str, script_path: Path, privileged: bool = True) -> str:
    relative = script_path.as_posix()
    options = (
        f"name: {json.dumps(name)}, "
        f"path: File.expand_path({json.dumps(relative)}, __dir__)"
    )
    if not privileged:
        options += ", privileged: false"
    return f'  config.vm.provision "shell", {options}\n'
