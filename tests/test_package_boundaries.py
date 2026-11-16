"""Check that qbotui does not depend on the separate lab or robot-control code."""

from __future__ import annotations

import re
import unittest
from pathlib import Path


class PackageBoundaryTest(unittest.TestCase):
    """Scan package source files for imports and features that must stay separate."""

    def test_package_source_has_no_lab_imports(self) -> None:
        """None of the forbidden imports, paths, or commands may appear in qbotui."""
        root = Path(__file__).resolve().parents[1] / "qbotui"
        # Each pattern describes one dependency or behavior the viewer must avoid.
        banned = (
            re.compile(r"^\s*import\s+pal\b", re.MULTILINE),
            re.compile(r"^\s*from\s+pal\b", re.MULTILINE),
            re.compile(r"^\s*import\s+quanser\b", re.MULTILINE),
            re.compile(r"^\s*from\s+quanser\b", re.MULTILINE),
            re.compile(r"\bsys\.path\b"),
            re.compile(r"quanser_lab[\\/]+quanser", re.IGNORECASE),
            re.compile(r"cv2\.imshow\b"),
            re.compile(r"\b18888\b"),
            re.compile(r"\bsubprocess\b"),
        )
        # Check every Python file in the package, including files in subfolders.
        sources = list(root.rglob("*.py"))
        self.assertTrue(sources)
        for path in sources:
            text = path.read_text(encoding="utf-8")
            for pattern in banned:
                self.assertIsNone(pattern.search(text), f"{path.name} matches {pattern.pattern}")
