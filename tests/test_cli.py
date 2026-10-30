import tempfile
import unittest
from pathlib import Path

from vagrant_sandbox.cli import main


class CliTests(unittest.TestCase):
    def test_no_up_generates_project_files(self):
        with tempfile.TemporaryDirectory() as directory:
            result = main(
                [
                    "create",
                    "--directory",
                    directory,
                    "--non-interactive",
                    "--no-up",
                ]
            )
            root = Path(directory)
            self.assertEqual(result, 0)
            self.assertTrue((root / "Vagrantfile").is_file())
            self.assertTrue((root / ".vagrant-sandbox" / "provision" / "user-setup.sh").is_file())


if __name__ == "__main__":
    unittest.main()
