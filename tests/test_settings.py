import tempfile
import unittest
from pathlib import Path

from vagrant_sandbox.settings import (
    default_provider,
    load_config,
    provider_requires_static_ip,
    resolve_settings,
)


class SettingsTests(unittest.TestCase):
    def test_base_profile_is_always_included(self):
        settings = resolve_settings({}, {"profiles": ["docker"]})
        self.assertEqual(settings.profiles, ("base", "docker"))

    def test_cli_overrides_config(self):
        settings = resolve_settings(
            {"vm_name": "from-config", "cpus": 4},
            {"vm_name": "from-cli", "cpus": None},
        )
        self.assertEqual(settings.vm_name, "from-cli")
        self.assertEqual(settings.cpus, 4)

    def test_rejects_invalid_ip_and_unknown_profile(self):
        for values in (
            {"vm_ip": "not-an-ip"},
            {"vm_ip": "8.8.8.8"},
            {"profiles": ["not-a-profile"]},
        ):
            with self.subTest(values=values), self.assertRaises(ValueError):
                resolve_settings(values, {})

    def test_custom_script_paths_are_relative_to_config(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            script = root / "install.sh"
            script.write_text("echo ready\n", encoding="utf-8")
            config_file = root / "config.json"
            config_file.write_text('{"custom_scripts": ["install.sh"]}', encoding="utf-8")
            config = load_config(config_file)
            settings = resolve_settings(config, {})
            self.assertEqual(settings.custom_scripts, (script.resolve(),))

    def test_interactive_values_override_defaults(self):
        answers = iter(
            ("devbox", "4", "4096", "generic/ubuntu2204", "virtualbox",
             "192.168.56.22", "base,python", "")
        )
        settings = resolve_settings({}, {}, interactive=True, input_fn=lambda _prompt: next(answers))
        self.assertEqual(settings.vm_name, "devbox")
        self.assertEqual(settings.cpus, 4)
        self.assertEqual(settings.profiles, ("base", "python"))
        self.assertEqual(settings.vm_ip, "192.168.56.22")
        self.assertEqual(settings.provider, "virtualbox")

    def test_provider_defaults_follow_host_platform(self):
        self.assertEqual(default_provider("win32", "AMD64"), "hyperv")
        self.assertEqual(default_provider("linux", "x86_64"), "libvirt")
        self.assertEqual(default_provider("darwin", "x86_64"), "virtualbox")
        self.assertEqual(default_provider("darwin", "arm64"), "virtualbox")

    def test_dynamic_provider_does_not_prompt_for_static_ip(self):
        answers = iter(("sandbox", "2", "2048", "generic/ubuntu2204", "hyperv", "", ""))
        prompted = []
        settings = resolve_settings(
            {},
            {},
            interactive=True,
            input_fn=lambda prompt: (prompted.append(prompt), next(answers))[1],
        )
        self.assertFalse(any("Private IPv4 address" in prompt for prompt in prompted))
        self.assertEqual(settings.provider, "hyperv")
        self.assertFalse(provider_requires_static_ip(settings.provider))

    def test_only_static_ip_providers_require_an_ip(self):
        settings = resolve_settings({"provider": "hyperv", "vm_ip": None}, {})
        self.assertIsNone(settings.vm_ip)
        with self.assertRaisesRegex(ValueError, "requires a private IPv4 address"):
            resolve_settings({"provider": "libvirt", "vm_ip": None}, {})


if __name__ == "__main__":
    unittest.main()
