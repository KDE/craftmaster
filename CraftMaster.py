import argparse
import configparser
import os
import shutil
import subprocess

import sys


class CraftMaster(object):
    def __init__(self, configFile, commands, variables, targets):
        self.commands = commands
        self.variables = variables or []
        self.targets = set(targets) if targets else set()
        self._setConfig(configFile)


    @property
    def defaultWorkDir(self):
        return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    def _init(self, workDir):
        if not subprocess.getoutput("git config --global --get url.git://anongit.kde.org/.insteadof") == "kde:":
            subprocess.run(["git", "config", "--global", "url.git://anongit.kde.org/.insteadOf", "kde:"])
            subprocess.run(["git", "config", "--global", "url.ssh://git@git.kde.org/.pushInsteadOf", "kde:"])
            subprocess.run(["git", "config", "--global", "core.autocrlf", "false"])
            subprocess.run(["git", "config", "--system", "core.autocrlf", "false"])
        craftClone = os.path.join(workDir, "craft-clone")
        if not os.path.exists(craftClone):
            subprocess.run(["git", "clone", "--depth=1", "kde:craft", craftClone], stderr=subprocess.PIPE)
        else:
            subprocess.run(["git", "pull"],  cwd=craftClone)

    def _setRoots(self, workDir, craftRoots):
        self.craftRoots = {}
        for root in craftRoots:
            craftRoot = os.path.abspath(os.path.join(workDir, root))
            if not os.path.isdir(craftRoot):
                os.makedirs(os.path.join(craftRoot, "etc"))
            if not os.path.isfile(os.path.join(craftRoot, "craft", "craftenv.ps1")):
                subprocess.run(["cmd", "/C", "mklink", "/J", os.path.join(craftRoot, "craft"), os.path.join(workDir, "craft-clone")])
            self.craftRoots[root] = craftRoot

    def _setConfig(self, configFile):
        if not os.path.isfile(configFile):
            print(f"Config file {configFile} does not exist.")
            exit(1)
        parser = configparser.ConfigParser(interpolation=configparser.ExtendedInterpolation())
        parser.optionxform = lambda option: option
        parser.read(configFile)
        if not "Variables" in parser.sections():
            parser.add_section("Variables")
        for var in self.variables:
            if not "=" in var:
                print(f"Invalid variable: {var}")
                exit(1)
            key, value = var.split("=", 1)
            parser["Variables"][key] = value
        if not "Root" in parser["Variables"]:
            parser["Variables"]["Root"] = self.defaultWorkDir
        with open(configFile + ".dump", "wt+" ) as dump:
            parser.write(dump)
        workDir = parser["Variables"]["Root"]

        targets = set(parser.sections())
        targets -= set(["General", "GeneralSettings", "Variables"])

        if self.targets:
            if not self.targets.issubset(targets):
                for n in self.targets - targets:
                    print(f"Target {n} is not a valid target. Valid targets are {targets}")
                exit(1)
        else:
            self.targets = targets

        if not self.targets:
            print("Please specify at least one target category")
            exit(1)

        self._init(workDir)

        self._setRoots(workDir, self.targets)

        if "GeneralSettings" in parser:
            self._setSetting(parser["GeneralSettings"].items(), clean=True)

        for root in self.targets:
            if root in parser:
                self._setSetting(parser[root].items(), [self.craftRoots[root]])

        if None in self.commands:
            if "Command" in parser["General"]:
                command = parser["General"]["Command"]
                if command:
                    self.commands = [c.strip().split(" ") for c in command.split(";")]
                else:
                    print("Please specify a command to run.\n"
                          "Either pass -c COMMAND to CraftMaster or set [General]Command in your configuration.")
                    exit(1)

    def _setSetting(self, settings, roots=None, clean=False):
        if not roots:
            roots = self.craftRoots.values()
        for craftDir in roots:
            parser = configparser.ConfigParser()
            ini = os.path.join(craftDir, "etc", "kdesettings.ini")
            if clean or not os.path.isfile(ini):
                parser.read(os.path.join(craftDir, "craft", "kdesettings.ini"))
            else:
                parser.read(ini)
            for key, value in settings:
                if not "/" in key:
                    print(f"Invalid option: {key} = {value}")
                    exit(1)
                sectin, key = key.split("/", 1)
                if not sectin in parser:
                    parser.add_section(sectin)
                parser[sectin][key] = value
            with open(ini, 'wt+') as configfile:
                parser.write(configfile)

            cache = os.path.join(craftDir, "etc", "cache.pickle")
            if os.path.exists(cache):
                os.remove(cache)

    def _exec(self, args):
        for craftDir  in sorted(self.craftRoots.values()):
            for command in args:
                print(f"{craftDir}: craft {' '.join(command)}")
                out = subprocess.run([sys.executable, os.path.join(craftDir, "craft", "bin", "craft.py")] + command)
                if not out.returncode == 0:
                    return  out.returncode
        return 0

    def run(self):
        return self._exec(self.commands)



if __name__ == "__main__":
    parser = argparse.ArgumentParser()
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

    master = CraftMaster(args.config, [args.commands], args.variables, args.targets)
    if args.print_targets:
        print("Targets:")
        for target in master.targets:
            print("\t", target)
    else:
        exit(master.run())
    exit(0)
