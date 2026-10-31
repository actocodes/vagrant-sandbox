import argparse
import sys
from pathlib import Path

from .generator import generate_project, start_vm
from .settings import AVAILABLE_PROFILES, load_config, resolve_settings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vagrant-sandbox",
        description="Generate and provision an isolated Vagrant development VM.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    create = subparsers.add_parser("create", help="Generate a Vagrantfile and start the VM.")
    create.add_argument("--config", type=Path, help="JSON configuration file.")
    create.add_argument(
        "--directory",
        type=Path,
        default=Path.cwd(),
        help="Project directory (default: current directory).",
    )
    create.add_argument("--vm-name")
    create.add_argument("--vm-ip")
    create.add_argument("--cpus", type=int)
    create.add_argument("--memory", type=int, help="VM memory in MB.")
    create.add_argument("--box")
    create.add_argument("--provider", help="Vagrant provider (for example virtualbox).")
    create.add_argument(
        "--profile",
        action="append",
        choices=AVAILABLE_PROFILES,
        dest="profiles",
        help="Provisioning profile; repeat to select multiple (default: base).",
    )
    create.add_argument(
        "--provision",
        action="append",
        type=Path,
        dest="custom_scripts",
        help="Custom shell provisioning script; repeat to add multiple.",
    )
    create.add_argument("--force", action="store_true", help="Replace generated files that already exist.")
    create.add_argument("--no-up", action="store_true", help="Generate files without running vagrant up.")
    create.add_argument("--non-interactive", action="store_true", help="Do not prompt; use config and defaults.")

    subparsers.add_parser("profiles", help="List built-in provisioning profiles.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "profiles":
        print("Available profiles:")
        print("  base    Common CLI tools, build essentials, Git, and workspace setup")
        print("  docker  Docker Engine")
        print("  nodejs  Node.js LTS")
        print("  python  Python 3, pip, and venv")
        return 0

    try:
        config = load_config(args.config)
        cli_values = {
            key: getattr(args, key)
            for key in (
                "vm_name",
                "vm_ip",
                "cpus",
                "memory",
                "box",
                "provider",
                "profiles",
                "custom_scripts",
            )
        }
        settings = resolve_settings(
            config,
            cli_values,
            interactive=not args.non_interactive and sys.stdin.isatty(),
        )
        vagrantfile = generate_project(settings, args.directory, force=args.force)
        print(f"Generated {vagrantfile}")
        if args.no_up:
            return 0
        result = start_vm(settings, args.directory.resolve())
        if result:
            print(f"vagrant up failed with exit code {result}.", file=sys.stderr)
        return result
    except (ValueError, OSError, RuntimeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
