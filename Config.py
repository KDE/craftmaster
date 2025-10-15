# -*- coding: utf-8 -*-
# Copyright Hannah von Reth <vonreth@kde.org>
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE REGENTS AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE REGENTS OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.

import configparser
import os
import platform
from pathlib import Path


class Config(object):
    ReservedSections = {
        "General",
        "GeneralSettings",
        "Variables",
        "BlueprintSettings",
        "Env",
    }

    @staticmethod
    def isWin():
        return os.name == "nt"

    @staticmethod
    def isUnix():
        return os.name == "posix"

    @staticmethod
    def isMac():
        return Config.isUnix() and platform.system() == "Darwin"

    @staticmethod
    def isLinux():
        return (
            Config.isUnix() and platform.system() == "Linux" and not Config.isAndroid()
        )

    @staticmethod
    def isAndroid():
        return "ANDROID_NDK" in os.environ

    @staticmethod
    def platformPrefix():
        if Config.isWin():
            return "windows"
        elif Config.isMac():
            return "macos"
        elif Config.isLinux():
            return "linux"
        elif Config.isAndroid():
            return "android"

    def __init__(self, configFiles: [Path], variables):
        self._targets = None
        self._config = configparser.ConfigParser(
            interpolation=configparser.ExtendedInterpolation(), allow_no_value=True
        )
        self._config.optionxform = str
        for configFile in configFiles:
            print(f"Reading config file {configFile}")
            if not configFile.is_file():
                print(f"Config file {configFile} does not exist.")
                exit(1)
            self._config.read(configFile, encoding="utf-8")
        if "Variables" not in self._config.sections():
            self._config.add_section("Variables")
        if variables:
            for var in variables:
                if "=" not in var:
                    print(f"Invalid variable: {var}")
                    exit(1)
                key, value = var.split("=", 1)
                self._config.set("Variables", key, value)
        self._config.set(
            "Variables", "Root", self.get("Variables", "Root", self.defaultWorkDir)
        )
        self._config.set("Variables", "CraftMasterRoot", os.path.dirname(__file__))
        self._config.set(
            "Variables",
            "CraftMasterConfigFolder",
            configFiles[0].parent.resolve().as_posix(),
        )
        if "Env" not in self._config.sections():
            self._config.add_section("Env")
        self._config["Env"].update(
            filter(lambda i: "$" not in i[0] and "$" not in i[1], os.environ.items())
        )

        if self.get("General", "DumpConfig", default=False):
            with open(f"{configFiles[0]}.dump", "wt+", encoding="UTF-8") as dump:
                for section, value in self._config.items():
                    dump.write(f"[{section}]\n")
                    dump.writelines(
                        [f"{k} = {v}\n" for k, v in value.items()] + ["\n\n"]
                    )

    def __contains__(self, key):
        if isinstance(key, tuple):
            return self._config.has_section(key[0]) and key[1] in self._config[key[0]]
        else:
            return self._config.has_section(key)

    @property
    def defaultWorkDir(self):
        return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    @property
    def targets(self):
        if not self._targets:
            platformPrefix = Config.platformPrefix()

            def _filter(x):
                if not x.startswith(platformPrefix):
                    return False
                abi, key = x.rsplit("-", 1)
                if key in {"BlueprintSettings", "Settings"}:
                    if abi not in targets:
                        print(f"Unable to find {abi} in targets")
                        exit(1)
                    return False
                return True

            targets = set(self._config.sections())
            targets -= Config.ReservedSections
            self._targets = list(filter(_filter, targets))
        return self._targets

    def getSection(self, section):
        return self._config[section].items()

    def get(self, section, key, default=configparser._UNSET, target=None):
        targetSection = f"{target}-{section}"
        if (targetSection, key) in self:
            return self._config.get(targetSection, key)
        if default != configparser._UNSET and not (section, key) in self:
            return default
        return self._config.get(section, key)

    def getBool(self, section, key, default=False, target=None):
        return self._config._convert_to_boolean(
            self.get(section, key, default=str(default), target=target)
        )

    @staticmethod
    def readIni(path=None):
        parser = configparser.ConfigParser(interpolation=None)
        parser.optionxform = str
        if path:
            parser.read(path, encoding="utf-8")
        return parser

    @staticmethod
    def writeIni(config, path):
        with open(path, "wt", encoding="utf-8") as configfile:
            print("#This file is autogenerated by CraftMaster", file=configfile)
            config.write(configfile)
