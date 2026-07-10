# SPDX-FileCopyrightText: 2026 Ralf Habacker <ralf.habacker@freenet.de>
#
# SPDX-License-Identifier: BSD-2-Clause

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from CraftMaster import CraftMaster


class CraftPackageExtractionTest(unittest.TestCase):
    def make_master(self):
        master = CraftMaster.__new__(CraftMaster)
        master.verbose = False
        return master

    def test_extracts_package_from_supported_title_formats(self):
        self.assertEqual(
            CraftMaster._extractPackageFromTitle("[kdeconnect-kde] Build package")[0],
            "kdeconnect-kde",
        )
        self.assertEqual(
            CraftMaster._extractPackageFromTitle("kate: Build package")[0],
            "kate",
        )

    def test_sets_craft_package_from_merge_request_title(self):
        with mock.patch.dict(
            os.environ,
            {
                "CI_MERGE_REQUEST_TITLE": "[kcalc] Build package",
            },
            clear=True,
        ):
            self.make_master()._setDefaultCraftPackage()
            self.assertEqual(os.environ["CRAFT_PACKAGE"], "kcalc")

    def test_invalid_github_event_path_warns_without_setting_craft_package(self):
        with mock.patch.dict(
            os.environ,
            {
                "GITHUB_EVENT_PATH": "/tmp/craftmaster-missing-event.json",
            },
            clear=True,
        ):
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                self.make_master()._setDefaultCraftPackage()

            self.assertNotIn("CRAFT_PACKAGE", os.environ)
            self.assertIn("Unable to use title source(s): GITHUB_EVENT_PATH", stderr.getvalue())
            self.assertIn(
                "Warning: CRAFT_PACKAGE was not set and no merge request", stderr.getvalue()
            )

    def test_sets_craft_package_from_github_pull_request_title(self):
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", delete=False
        ) as event_file:
            json.dump({"pull_request": {"title": "okular: Build package"}}, event_file)
            event_path = event_file.name

        try:
            with mock.patch.dict(
                os.environ,
                {
                    "GITHUB_EVENT_PATH": event_path,
                },
                clear=True,
            ):
                self.make_master()._setDefaultCraftPackage()
                self.assertEqual(os.environ["CRAFT_PACKAGE"], "okular")
        finally:
            os.unlink(event_path)

    def test_determine_package_option_prints_detected_package_without_config(self):
        env = {
            "PATH": os.environ["PATH"],
            "CI_COMMIT_TITLE": "kcalc: Build package",
        }
        completed = subprocess.run(
            [sys.executable, "CraftMaster.py", "--determine-package"],
            check=True,
            encoding="utf-8",
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        self.assertEqual(completed.stdout.strip(), "kcalc")


if __name__ == "__main__":
    unittest.main()
