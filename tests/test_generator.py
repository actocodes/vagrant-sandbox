from contextlib import redirect_stderr
from io import StringIO
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from vagrant_sandbox.generator import (
    _ensure_no_conflicting_linux_guests,
    _linux_provider,
    generate_project,
    render_vagrantfile,
    start_vm,
)
from vagrant_sandbox.settings import default_provider, resolve_settings


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
        self.assertIn("def vagrant_sandbox_remove_ssh_config", content)
        self.assertIn("vagrant_sandbox_remove_ssh_config", content)
        self.assertIn('trigger.name = "vagrant-sandbox host config cleanup"', content)
        self.assertIn('vagrant_sandbox_update_hosts("add", address)', content)
        self.assertIn('vagrant_sandbox_update_hosts("remove")', content)
        self.assertIn('$path = Join-Path $env:SystemRoot "System32\\\\drivers\\\\etc\\\\hosts"', content)
        self.assertIn('hosts_path = "/etc/hosts"', content)
        self.assertIn("Start-Process -FilePath \"powershell.exe\" -Verb RunAs", content)
        self.assertIn('config.vm.network "private_network", ip: VM_IP', content)
        self.assertIn('config.vm.provider "libvirt" do |libvirt|', content)
        self.assertIn('config.vm.box_architecture = "arm64" if ARM64_HOST', content)
        self.assertIn('libvirt.driver = "kvm"', content)
        self.assertIn('libvirt.graphics_type = "none"', content)
        self.assertIn('libvirt__network_name: "vagrant-sandbox"', content)
        self.assertIn('ENV["VAGRANT_DEFAULT_PROVIDER"] ||= default_provider if default_provider', content)
        self.assertIn('config.vm.provision "sandbox-dns"', content)
        self.assertIn("DNSSEC=no", content)
        self.assertIn("getent hosts mirrors.edge.kernel.org", content)
        self.assertIn('"--usb", "off"', content)
        self.assertIn('"--usb-autoconnect", "off"', content)
        self.assertNotIn("@@", content)

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
        answers = iter(("", "", "", "", "", "", ""))
        settings = resolve_settings(
            {"provider": "virtualbox"},
            {},
            interactive=True,
            input_fn=lambda _prompt: next(answers),
        )
        self.assertEqual(settings.provider, default_provider())

    def test_start_vm_passes_provider_without_shell(self):
        settings = resolve_settings({}, {"provider": "virtualbox"})
        with patch("vagrant_sandbox.generator.subprocess.run") as run:
            run.return_value.returncode = 0
            self.assertEqual(start_vm(settings, Path(".")), 0)
            run.assert_called_once_with(
                ["vagrant", "up", "--provider", "virtualbox"], cwd=Path("."), check=False
            )

    def test_linux_uses_virtualbox_when_libvirt_is_not_ready(self):
        warning = StringIO()
        with redirect_stderr(warning):
            with (
                patch("vagrant_sandbox.generator.subprocess.run") as run,
                patch(
                    "vagrant_sandbox.generator.shutil.which",
                    return_value="VBoxManage",
                ),
            ):
                run.return_value.returncode = 0
                run.return_value.stdout = ""
                self.assertEqual(_linux_provider(), "virtualbox")
        self.assertIn("using the VirtualBox fallback", warning.getvalue())

    def test_linux_refuses_to_mix_running_hypervisors(self):
        with (
            patch("vagrant_sandbox.generator.shutil.which", return_value="VBoxManage"),
            patch("vagrant_sandbox.generator.subprocess.run") as run,
        ):
            run.return_value.returncode = 0
            run.return_value.stdout = '"existing-vm" {abc}\n'
            with self.assertRaisesRegex(RuntimeError, "must not run together"):
                _ensure_no_conflicting_linux_guests("libvirt")

    def test_hyperv_requires_an_elevated_windows_shell(self):
        settings = resolve_settings({}, {"provider": "hyperv"})
        with (
            patch("vagrant_sandbox.generator.os.name", "nt"),
            patch("vagrant_sandbox.generator._is_windows_admin", return_value=False),
            patch("vagrant_sandbox.generator.subprocess.run") as run,
        ):
            with self.assertRaisesRegex(RuntimeError, "elevated Administrator shell"):
                start_vm(settings, Path("."))
            run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
