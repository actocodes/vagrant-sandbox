import json
import shutil
import subprocess
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
    command = ["vagrant", "up"]
    if settings.provider:
        command.extend(["--provider", settings.provider])
    try:
        result = subprocess.run(command, cwd=output_dir, check=False)
    except FileNotFoundError as error:
        raise RuntimeError(
            "Vagrant was not found. Install Vagrant and ensure it is on PATH."
        ) from error
    return result.returncode


def _provision_block(name: str, script_path: Path, privileged: bool = True) -> str:
    relative = script_path.as_posix()
    options = (
        f"name: {json.dumps(name)}, "
        f"path: File.expand_path({json.dumps(relative)}, __dir__)"
    )
    if not privileged:
        options += ", privileged: false"
    return f'  config.vm.provision "shell", {options}\n'
