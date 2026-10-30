import tempfile
import unittest
from pathlib import Path

from vagrant_sandbox.settings import load_config, resolve_settings


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
        answers = iter(("devbox", "192.168.56.22", "4", "4096", "ubuntu/jammy64", "", "base,python", ""))
        settings = resolve_settings({}, {}, interactive=True, input_fn=lambda _prompt: next(answers))
        self.assertEqual(settings.vm_name, "devbox")
        self.assertEqual(settings.cpus, 4)
        self.assertEqual(settings.profiles, ("base", "python"))


if __name__ == "__main__":
    unittest.main()
