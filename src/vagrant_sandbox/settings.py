import ipaddress
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


DEFAULTS: dict[str, Any] = {
    "vm_name": "sandbox",
    "vm_ip": "192.168.56.10",
    "cpus": 2,
    "memory": 2048,
    "box": "bento/ubuntu-24.04",
    "provider": None,
    "profiles": ["base"],
    "custom_scripts": [],
}
ALLOWED_CONFIG_KEYS = frozenset(DEFAULTS)
AVAILABLE_PROFILES = ("base", "docker", "nodejs", "python")
PRIVATE_NETWORKS = tuple(
    ipaddress.ip_network(network)
    for network in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")
)


@dataclass(frozen=True)
class Settings:
    vm_name: str
    vm_ip: str
    cpus: int
    memory: int
    box: str
    provider: str | None
    profiles: tuple[str, ...]
    custom_scripts: tuple[Path, ...]


def load_config(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    try:
        with path.open(encoding="utf-8") as config_file:
            data = json.load(config_file)
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Could not read config file '{path}': {error}") from error
    if not isinstance(data, dict):
        raise ValueError("Config file must contain a JSON object.")
    unknown = set(data) - ALLOWED_CONFIG_KEYS
    if unknown:
        raise ValueError(f"Unknown config option(s): {', '.join(sorted(unknown))}")
    if "custom_scripts" in data:
        scripts = data["custom_scripts"]
        if not isinstance(scripts, list) or not all(isinstance(item, str) for item in scripts):
            raise ValueError("'custom_scripts' must be a list of file paths.")
        data["custom_scripts"] = [
            (path.parent / item).resolve() if not Path(item).is_absolute() else Path(item)
            for item in scripts
        ]
    return data


def resolve_settings(
    config: dict[str, Any],
    cli: dict[str, Any],
    interactive: bool = False,
    input_fn: Callable[[str], str] = input,
) -> Settings:
    values = {**DEFAULTS, **config}
    for key, value in cli.items():
        if value is not None:
            if key == "custom_scripts":
                values[key] = [*values["custom_scripts"], *value]
            else:
                values[key] = value

    if interactive:
        prompts = (
            ("vm_name", "VM name"),
            ("vm_ip", "Private IPv4 address"),
            ("cpus", "CPU cores"),
            ("memory", "Memory in MB"),
            ("box", "Vagrant box"),
            ("provider", "Provider (blank for Vagrant default)"),
            ("profiles", "Provisioning profiles (comma-separated)"),
            ("custom_scripts", "Custom shell scripts (comma-separated paths)"),
        )
        for key, label in prompts:
            if cli.get(key) is not None:
                continue
            current = values[key]
            if key in ("profiles", "custom_scripts"):
                shown = ", ".join(str(item) for item in current)
            else:
                shown = "" if current is None else str(current)
            answer = input_fn(f"{label} [{shown}]: ").strip()
            if not answer:
                if key == "provider":
                    values[key] = None
                continue
            if key in ("profiles", "custom_scripts"):
                items = [item.strip() for item in answer.split(",") if item.strip()]
                values[key] = items if key == "profiles" else [
                    Path(item).expanduser().resolve() for item in items
                ]
            elif key in ("cpus", "memory"):
                try:
                    values[key] = int(answer)
                except ValueError as error:
                    raise ValueError(f"{label} must be an integer.") from error
            else:
                values[key] = answer or None

    return validate_settings(values)


def validate_settings(values: dict[str, Any]) -> Settings:
    vm_name = values["vm_name"]
    if not isinstance(vm_name, str) or not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9_-]{0,62}", vm_name
    ):
        raise ValueError(
            "VM name must be 1-63 letters, digits, hyphens, or underscores and start with a letter or digit."
        )

    vm_ip = values["vm_ip"]
    if not isinstance(vm_ip, str):
        raise ValueError("VM IP must be a valid private IPv4 address.")
    try:
        ip = ipaddress.ip_address(vm_ip)
    except (TypeError, ValueError) as error:
        raise ValueError("VM IP must be a valid IPv4 or IPv6 address.") from error
    if not isinstance(ip, ipaddress.IPv4Address):
        raise ValueError("VM IP must be IPv4 for Vagrant's host-only network.")
    if not any(ip in network for network in PRIVATE_NETWORKS):
        raise ValueError(
            "VM IP must belong to a private IPv4 range (10/8, 172.16/12, or 192.168/16)."
        )

    cpus = _bounded_integer(values["cpus"], "CPU count", 1, 256)
    memory = _bounded_integer(values["memory"], "Memory", 512, 1_048_576)
    box = values["box"]
    if not isinstance(box, str) or not box.strip() or any(char in box for char in "\r\n"):
        raise ValueError("Vagrant box must be a non-empty single-line string.")

    provider = values["provider"]
    if provider is not None and (
        not isinstance(provider, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", provider)
    ):
        raise ValueError("Provider must contain only letters, digits, hyphens, or underscores.")

    profiles_value = values["profiles"]
    if not isinstance(profiles_value, (list, tuple)) or not all(
        isinstance(item, str) for item in profiles_value
    ):
        raise ValueError("'profiles' must be a list of profile names.")
    profiles = list(dict.fromkeys(profiles_value))
    unknown_profiles = set(profiles) - set(AVAILABLE_PROFILES)
    if unknown_profiles:
        raise ValueError(f"Unknown profile(s): {', '.join(sorted(unknown_profiles))}")
    if not profiles:
        profiles = ["base"]
    if "base" not in profiles:
        profiles.insert(0, "base")

    scripts_value = values["custom_scripts"]
    if not isinstance(scripts_value, (list, tuple)):
        raise ValueError("'custom_scripts' must be a list of file paths.")
    scripts: list[Path] = []
    for script in scripts_value:
        if not isinstance(script, (str, Path)):
            raise ValueError("Each custom provisioning script must be a file path.")
        path = Path(script).expanduser().resolve()
        if not path.is_file():
            raise ValueError(f"Custom provisioning script does not exist: {path}")
        scripts.append(path)

    return Settings(
        vm_name=vm_name,
        vm_ip=str(ip),
        cpus=cpus,
        memory=memory,
        box=box.strip(),
        provider=provider,
        profiles=tuple(profiles),
        custom_scripts=tuple(scripts),
    )


def _bounded_integer(value: Any, label: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise ValueError(f"{label} must be between {minimum} and {maximum}.")
    return value
