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


class Config(object):
    ReservedSections = {"General", "GeneralSettings", "Variables", "BlueprintSettings"}

    def __init__(self, configFile, variables):
        self._targets = None

        if not os.path.isfile(configFile):
            print(f"Config file {configFile} does not exist.")
            exit(1)
        self._config = configparser.ConfigParser(interpolation=configparser.ExtendedInterpolation())
        self._config.optionxform = lambda option: option
        self._config.read(configFile)
        if not "Variables" in self._config.sections():
            self._config.add_section("Variables")
        if variables:
            for var in variables:
                if not "=" in var:
                    print(f"Invalid variable: {var}")
                    exit(1)
                key, value = var.split("=", 1)
                self._config.set("Variables", key, value)
        self._config.set("Variables", "Root", self.get("Variables", "Root", self.defaultWorkDir))

        if self.getSetting("DumpConfig", default=False):
            with open(configFile + ".dump", "wt+") as dump:
                self._config.write(dump)



    def __contains__( self, key ):
        if isinstance(key, tuple):
            return self._config.has_section(key[0]) and key[1] in self._config[key[0]]
        else:
            return self._config.has_section( key )

    @property
    def defaultWorkDir(self):
        return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


    def getSetting(self, key, target=None, default=configparser._UNSET):
        if target:
            section = f"{target}-settings"
            return self.get(section, key, self.get("General", key, default=default))
        return self.get("General", key, default=default)


    @property
    def targets(self):
        if not self._targets:
            targets = set(self._config.sections())
            targets -= Config.ReservedSections
            for x in targets.copy():
                if x.endswith("-settings"):
                    targets.remove(x)
                    key = x.replace("-settings", "")
                    if not key in targets:
                        print(f"Unable to find {key} in targets")
                        exit(1)
            self._targets = targets
        return self._targets

    def getSection(self, section):
        return self._config[section].items()


    def get(self, section, key, default=configparser._UNSET):
        if default != configparser._UNSET and not (section, key) in self:
            return default
        return self._config.get(section, key)

    def getBool(self, section, key, default=False):
        return self._config._convert_to_boolean(self.get(section, key, default=str(default)))
