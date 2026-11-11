import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from vagrant_sandbox.generator import generate_project, render_vagrantfile, start_vm
from vagrant_sandbox.settings import resolve_settings


class GeneratorTests(unittest.TestCase):
    def test_render_preserves_isolation_and_selected_provisioners(self):
        settings = resolve_settings({}, {"vm_name": "testbox", "profiles": ["nodejs"]})
        content = render_vagrantfile(settings)
        self.assertIn('config.vm.synced_folder ".", "/vagrant", disabled: true', content)
        self.assertIn("config.ssh.forward_agent = false", content)
        self.assertIn('name: "profile-base"', content)
        self.assertIn('name: "profile-nodejs"', content)
        self.assertIn('name: "user-setup"', content)
        self.assertIn("privileged: false", content)
        self.assertIn('VM_NAME = "testbox"', content)
        self.assertIn("config.trigger.after :up, :reload do |trigger|", content)
        self.assertIn("ssh_info = machine.ssh_info", content)
        self.assertIn('host_alias = "sandbox-#{VM_NAME}"', content)
        self.assertIn('File.expand_path("~/.ssh/config")', content)
        self.assertIn('vagrant_sandbox_update_hosts("add")', content)
        self.assertIn('vagrant_sandbox_update_hosts("remove")', content)
        self.assertIn('$path = Join-Path $env:SystemRoot "System32\\\\drivers\\\\etc\\\\hosts"', content)
        self.assertIn('hosts_path = "/etc/hosts"', content)
        self.assertIn("Start-Process -FilePath \"powershell.exe\" -Verb RunAs", content)
        self.assertIn('config.vm.network "private_network", ip: VM_IP', content)

    def test_generation_refuses_to_replace_without_force(self):
        settings = resolve_settings({}, {})
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            (output / "Vagrantfile").write_text("keep me", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                generate_project(settings, output)
            self.assertEqual((output / "Vagrantfile").read_text(encoding="utf-8"), "keep me")

    def test_custom_script_is_copied_and_referenced(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            custom_script = root / "custom.sh"
            custom_script.write_text("echo custom\n", encoding="utf-8")
            settings = resolve_settings({}, {"custom_scripts": [custom_script]})
            output = root / "project"
            generate_project(settings, output)
            self.assertEqual(
                (output / ".vagrant-sandbox" / "provision" / "custom-1-custom.sh").read_text(encoding="utf-8"),
                "echo custom\n",
            )
            generated = (output / "Vagrantfile").read_text(encoding="utf-8")
            self.assertIn("custom-1-custom.sh", generated)

    def test_interactive_blank_provider_clears_configured_provider(self):
        answers = iter(("", "", "", "", "", "", "", ""))
        settings = resolve_settings(
            {"provider": "virtualbox"},
            {},
            interactive=True,
            input_fn=lambda _prompt: next(answers),
        )
        self.assertIsNone(settings.provider)

    def test_start_vm_passes_provider_without_shell(self):
        settings = resolve_settings({}, {"provider": "virtualbox"})
        with patch("vagrant_sandbox.generator.subprocess.run") as run:
            run.return_value.returncode = 0
            self.assertEqual(start_vm(settings, Path(".")), 0)
            run.assert_called_once_with(
                ["vagrant", "up", "--provider", "virtualbox"], cwd=Path("."), check=False
            )


if __name__ == "__main__":
    unittest.main()
