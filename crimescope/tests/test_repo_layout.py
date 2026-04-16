import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class RepoLayoutTest(unittest.TestCase):
    def test_expected_directories_exist(self) -> None:
        expected = [
            "frontend",
            "backend",
            "workers",
            "infra",
            "notebooks",
            "data_samples",
            "docs",
        ]
        for folder in expected:
            with self.subTest(folder=folder):
                self.assertTrue((REPO_ROOT / folder).is_dir())


if __name__ == "__main__":
    unittest.main()

