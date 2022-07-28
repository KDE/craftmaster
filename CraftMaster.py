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

import argparse
import configparser
import errno
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

from Config import Config


class CraftMaster(object):
    def __init__(self, configFiles : [str], commands, variables, targets, setup : bool=False ,verbose=False):
        self.commands = [commands] if commands else []
        self.targets = set(targets) if targets else set()
        self.verbose = verbose
        self.doSetup = setup
        self._setConfig(configFiles, variables)

    #https://stackoverflow.com/a/1214935
    @staticmethod
    def __handleRemoveReadonly(func, path, exc):
        excvalue = exc[1]
        if func in (os.rmdir, os.remove, os.unlink) and excvalue.errno == errno.EACCES:
            os.chmod(path, stat.S_IRWXU| stat.S_IRWXG| stat.S_IRWXO) # 0777
            func(path)
        else:
            raise Exception()

    def _log(self, text, stream=sys.stdout):
        print(text, file=stream)

    def _error(self, text, fatal=True):
        self._log(text, stream=sys.stderr)
        if fatal:
            exit(1)

    def _debug(self, text):
        if self.verbose:
            self._log(text)

    def _run(self, args, **kwargs):
        command = " ".join(args)
        self._debug(command)
        out = subprocess.run(args, stderr=subprocess.STDOUT, **kwargs)
        if not out.returncode == 0:
            self._error(f"Command {command} failed with exit code: {out.returncode}")

    def _init(self, workDir):
        craftClone = os.path.join(workDir, "craft-clone")
        branch = self.config.get("General", "Branch", "master")
        forceClone = self.config.getBool("General", "ForceClone", False)
        shallowClone = self.config.getBool("General", "ShallowClone", False)
        craftUrl = self.config.get("General", "CraftUrl", "https://invent.kde.org/kde/craft.git")
        args = []
        if shallowClone:
            args += ["--depth=1", "--no-single-branch"]
        if forceClone and os.path.exists(craftClone):
            shutil.rmtree(craftClone, onerror=CraftMaster.__handleRemoveReadonly)

        if not os.path.exists(craftClone):
            self._run(["git", "clone", "--branch", branch] + args + [craftUrl, craftClone])

        revision = self.config.get("General", "CraftRevision", None)
        if revision:
            self._run(["git", "checkout", "-f", revision])

    def _setRoots(self, workDir, craftRoots):
        self.craftRoots = {}
        for root in craftRoots:
            craftRoot = os.path.abspath(os.path.join(workDir, self.config.get("Settings", "Root", root, target=root)))
            os.makedirs(os.path.join(craftRoot, "etc"), exist_ok=True)
            if not os.path.isfile(os.path.join(craftRoot, "craft", "craftenv.ps1")):
                src = os.path.join(workDir, "craft-clone")
                dest =  os.path.join(craftRoot, "craft")
                if Config.isWin():
                    self._run(["cmd", "/C", "mklink", "/J", dest.replace("/", "\\"), src.replace("/", "\\")])
                else:
                    os.symlink(src, dest, target_is_directory=True)
            self.craftRoots[root] = craftRoot


    def _setConfig(self, configFiles, variables):
        self.config = Config(configFiles, variables)

        workDir = self.config.get("Variables", "Root")

        if self.targets:
            if not self.targets.issubset(self.config.targets):
                for n in self.targets - set(self.config.targets):
                    self._error(f"Target {n} is not a valid target. Valid targets are {self.config.targets}", fatal=False)
                exit(1)
        else:
            self.targets = self.config.targets

        if not self.targets:
            self._error("Please specify at least one target category")

        self._init(workDir)
        self._setRoots(workDir, self.targets)

        for root in self.targets:
            craftDir = self.craftRoots[root]
            blueprintSetting = Config.readIni()
            # TODO: use ini?
            setupFile =  Path(craftDir) / "etc/craftmaster_setup"
            if not self.doSetup and setupFile.exists():
                continue
            if self.doSetup:
                setupFile.touch()
            self._log("Generate Settings", stream=sys.stderr)

            if "BlueprintSettings" in self.config:
                self._setBluePrintSettings(self.config.getSection("BlueprintSettings"), config=blueprintSetting)

            if f"{root}-BlueprintSettings" in self.config:
                self._setBluePrintSettings(self.config.getSection(f"{root}-BlueprintSettings"), config=blueprintSetting)

            Config.writeIni(blueprintSetting, os.path.join(craftDir, "etc", "BlueprintSettings.ini"))

            settingsFile = os.path.join(craftDir, "craft", "CraftSettings.ini.template")
            if not os.path.exists(settingsFile):
                self._error(f"{settingsFile} does not exist")
            try:
                settings = Config.readIni(settingsFile)
                # add ourself to the blueprints
                settings.set("Blueprints", "Locations", f"{os.path.dirname(os.path.abspath(__file__))}/blueprints;" + settings["Blueprints"].get("Locations", ""))

                if "GeneralSettings" in self.config:
                    self._setSetting(self.config.getSection("GeneralSettings"), config=settings)

                if f"{root}-GeneralSettings" in self.config:
                    # this doesn't make any sense?
                    self._log(f"Please replace the config: '{root}-GeneralSettings'  with '{root}' ")
                    self._setSetting(self.config.getSection(f"{root}-GeneralSettings"), config=settings)

                if root in self.config:
                    self._setSetting(self.config.getSection(root), config=settings)

                Config.writeIni(settings, os.path.join(craftDir, "etc", "CraftSettings.ini"))

                cache = os.path.join(craftDir, "etc", "cache.pickle")
                if os.path.exists(cache):
                    os.remove(cache)
            except Exception as e:
                    with open(settingsFile, "rt") as f:
                       self._error(f"Failed to setup settings {settingsFile}\n{e}\n\nTemplate:\n{f.read()}")


    def _setSetting(self, settings, config):
        for key, value in settings:
            if not "/" in key:
                self._error(f"Invalid option: {key} = {value}")
            sectin, key = key.split("/", 1)
            if not sectin in config:
                config.add_section(sectin)
            config[sectin][key] = value


    def _setBluePrintSettings(self, settings, config):
        for key, value in settings:
            if not "." in key:
                self._error(f"Invalid BlueprintSetting: {key} = {value}")
            sectin, key = key.split(".", 1)
            if sectin not in config:
                config.add_section(sectin)
            config[sectin][key] = value

    def _exec(self, target, args):
        craftDir = self.craftRoots[target]
        for command in args:
            self._run([sys.executable, "-X", "utf8", "-u", os.path.join(craftDir, "craft", "bin", "craft.py")] + command)

    def run(self):
        for target in sorted(self.craftRoots.keys()):
            commands = self.commands
            if not commands:
                commands = self.config.get("General", "Command", None)
                if commands:
                    commands = [c.strip().split(" ") for c in commands.split(";") if c]
                if not commands:
                    return
            self._exec(target, commands)



if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="Craft Master")
    parser.add_argument("--version", action="version", version="%(prog)s 0.2.9")
    parser.add_argument("--verbose", action="store_true",
                        help="Enable verbose logging of CraftMaster")
    parser.add_argument("--config", action="store", required=True,
                        help="The path to the configuration file.")
    parser.add_argument("--setup", action="store_true",
                        help="When this option is provided, regeneration of the generated settings will only be performed explicitly by setting this flag.")
    parser.add_argument("--config-override", action="append", default=[],
                        help="The path to a configuration override.")
    parser.add_argument("--variables", action="store", nargs="+",
                        help="Set values for the [Variables] section in the configuration.")
    parser.add_argument("--targets", action="store", nargs="+",
                        help="Only use on a subset of targets")
    parser.add_argument("--print-targets", action="store_true",
                        help="Print all available targets.")
    parser.add_argument("-c", "--commands", nargs=argparse.REMAINDER,
                        help="Commands executed on the targets. By default the command form the configuration is used." )

    args = parser.parse_args()
    configs = [args.config]
    configs += args.config_override
    master = CraftMaster(configs, args.commands, args.variables, args.targets, setup=args.setup, verbose=args.verbose)
    if args.print_targets:
        print("Targets:")
        for target in master.targets:
            print("\t", target)
    else:
        exit(master.run())
    exit(0)
