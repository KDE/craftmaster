# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: Hannah von Reth <vonreth@kde.org>
#
# SPDX-License-Identifier: BSD-2-Clause

import os

import info
from Package.BlueprintRepositoryPackageBase import BlueprintRepositoryPackageBase


class subinfo(info.infoclass):
    def setTargets(self):
        for ver in ["master", "stable"]:
            self.svnTargets[ver] = (
                f"https://invent.kde.org/packaging/craftmaster.git|{ver}|"
            )
            self.targetUpdatedRepoUrl[ver] = (
                "git://anongit.kde.org/craftmaster",
                "https://invent.kde.org/packaging/craftmaster.git",
            )
        self.defaultTarget = "master"


class Package(BlueprintRepositoryPackageBase):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.subinfo.shelveAble = False

    def checkoutDir(self, index=0):
        return os.path.join(os.path.dirname(__file__), "..", "..", "..")
