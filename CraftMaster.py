import argparse
import configparser
import os
import shutil
import subprocess

import sys

from Config import Config


class CraftMaster(object):
    def __init__(self, configFile, commands, variables, targets, verbose=False):
        self.commands = [commands] if commands else []
        self.targets = set(targets) if targets else set()
        self.branch = "master"
        self.shallowClone = True
        self.verbose = verbose
        self._setConfig(configFile, variables)

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
        if not os.path.exists(craftClone):
            args = []
            if self.shallowClone:
                if self.branch == "master":
                    args += ["--depth=1"]
                else:
                    args += ["--branch", self.branch]
            self._run(["git", "clone"] + args + ["git://anongit.kde.org/craft.git", craftClone])

    def _setRoots(self, workDir, craftRoots):
        self.craftRoots = {}
        for root in craftRoots:
            craftRoot = os.path.abspath(os.path.join(workDir, root))
            if not os.path.isdir(craftRoot):
                os.makedirs(os.path.join(craftRoot, "etc"))
            if not os.path.isfile(os.path.join(craftRoot, "craft", "craftenv.ps1")):
                self._run(["cmd", "/C", "mklink", "/J", os.path.join(craftRoot, "craft"), os.path.join(workDir, "craft-clone")])
            self.craftRoots[root] = craftRoot


    def _setConfig(self, configFile, variables):
        self.config = Config(configFile, variables)

        workDir = self.config.get("Variables", "Root")

        if self.targets:
            if not self.targets.issubset(self.config.targets):
                for n in self.targets - self.config.targets:
                    self._error(f"Target {n} is not a valid target. Valid targets are {self.config.targets}", fatal=False)
                exit(1)
        else:
            self.targets = self.config.targets

        if not self.targets:
            self._error("Please specify at least one target category")

        self.branch = self.config.get("General", "Branch", self.branch)
        self.shallowClone = self.config.getBool("General", "ShallowClone", True)

        self._init(workDir)
        self._setRoots(workDir, self.targets)

        for root in self.targets:
            craftDir = craftDir=self.craftRoots[root]
            if "BlueprintSettings" in self.config:
                self._setBluePrintSettings(self.config.getSection("BlueprintSettings"), craftDir=craftDir)

            if "GeneralSettings" in self.config:
                self._setSetting(self.config.getSection("GeneralSettings"), craftDir=craftDir, clean=True)
            if root in self.config:
                self._setSetting(self.config.getSection(root), craftDir=craftDir)


    def _setSetting(self, settings, craftDir, clean=False):
        parser = configparser.ConfigParser()
        ini = os.path.join(craftDir, "etc", "CraftSettings.ini")
        if clean or not os.path.isfile(ini):
            parser.read(os.path.join(craftDir, "craft", "CraftSettings.ini.template"))
        else:
            parser.read(ini)
        for key, value in settings:
            if not "/" in key:
                self._error(f"Invalid option: {key} = {value}")
            sectin, key = key.split("/", 1)
            if not sectin in parser:
                parser.add_section(sectin)
            parser[sectin][key] = value
        with open(ini, 'wt+') as configfile:
            parser.write(configfile)

        cache = os.path.join(craftDir, "etc", "cache.pickle")
        if os.path.exists(cache):
            os.remove(cache)

    def _setBluePrintSettings(self, settings, craftDir):
        parser = configparser.ConfigParser()
        ini = os.path.join(craftDir, "etc", "BlueprintSettings.ini")
        for key, value in settings:
            if not "." in key:
                self._error(f"Invalid BlueprintSetting: {key} = {value}")
            sectin, key = key.split(".", 1)
            if not sectin in parser:
                parser.add_section(sectin)
            parser[sectin][key] = value
        with open(ini, 'wt+') as configfile:
            parser.write(configfile)

    def _exec(self, craftDir, args):
        for command in args:
            self._run([sys.executable, os.path.join(craftDir, "craft", "bin", "craft.py")] + command)

    def run(self):
        for target, craftDir in sorted(self.craftRoots.items()):
            commands = self.commands
            if not commands:
                commands = self.config.getSetting("Command", target, None)
                if commands:
                    commands = [c.strip().split(" ") for c in commands.split(";")]
                if not commands:
                    return
            self._exec(craftDir, commands)



if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="Craft Master")
    parser.add_argument("--version", action="version", version="%(prog)s 0.2.9")
    parser.add_argument("--verbose", action="store_true",
                        help="Enable verbose logging of CraftMaster")
    parser.add_argument("--config", action="store", required=True,
                        help="The path to the configuration file.")
    parser.add_argument("--variables", action="store", nargs="+",
                        help="Set values for the [Variables] section in the configuration.")
    parser.add_argument("--targets", action="store", nargs="+",
                        help="Only use on a subset of targets")
    parser.add_argument("--print-targets", action="store_true",
                        help="Print all available targets.")
    parser.add_argument("-c", "--commands", nargs=argparse.REMAINDER,
                        help="Commands executed on the taargets. By default the coammand form the configuration is used." )

    args = parser.parse_args()

    master = CraftMaster(args.config, args.commands, args.variables, args.targets, verbose=args.verbose)
    if args.print_targets:
        print("Targets:")
        for target in master.targets:
            print("\t", target)
    else:
        exit(master.run())
    exit(0)
