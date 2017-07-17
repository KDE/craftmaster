import argparse
import configparser
import os
import shutil
import subprocess

import sys

from Config import Config


class CraftMaster(object):
    def __init__(self, configFile, commands, variables, targets):
        self.commands = commands or []
        self.targets = set(targets) if targets else set()
        self.branch = "master"
        self._setConfig(configFile, variables)
        self.shallowClone = True

    def _run(self, args, **kwargs):
        command = " ".join(args)
        print(command)
        out = subprocess.run(args, stderr=subprocess.STDOUT, **kwargs)
        if not out.returncode == 0:
            print(f"Command {command} failed with exit code: {out.returncode}")
            exit(1)

    def _init(self, workDir):
        if not subprocess.getoutput("git config --global --get url.git://anongit.kde.org/.insteadof") == "kde:":
            self._run(["git", "config", "--global", "url.git://anongit.kde.org/.insteadOf", "kde:"])
            self._run(["git", "config", "--global", "url.ssh://git@git.kde.org/.pushInsteadOf", "kde:"])
            self._run(["git", "config", "--global", "core.autocrlf", "false"])
            self._run(["git", "config", "--system", "core.autocrlf", "false"])
        craftClone = os.path.join(workDir, "craft-clone")
        if not os.path.exists(craftClone):
            args = []
            if self.shallowClone:
                if self.branch == "master":
                    args += ["--depth=1"]
                else:
                    args += ["--branch", self.branch]
            self._run(["git", "clone"] + args + ["kde:craft", craftClone])
        self._run(["git", "fetch"],  cwd=craftClone)
        self._run(["git", "checkout", self.branch],  cwd=craftClone)
        self._run(["git", "pull"],  cwd=craftClone)

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
                    print(f"Target {n} is not a valid target. Valid targets are {self.config.targets}")
                exit(1)
        else:
            self.targets = self.config.targets

        if not self.targets:
            print("Please specify at least one target category")
            exit(1)

        self.branch = self.config.get("General", "Branch", self.branch)
        self.shallowClone = self.config.getBool("General", "ShallowClone", True)

        self._init(workDir)
        self._setRoots(workDir, self.targets)

        if "GeneralSettings" in self.config:
            self._setSetting(self.config.getSection("GeneralSettings"), clean=True)

        for root in self.targets:
            if root in self.config:
                self._setSetting(self.config.getSection(root), [self.craftRoots[root]])


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

    def _exec(self, craftDir, args):
        for command in args:
            self._run([sys.executable, os.path.join(craftDir, "craft", "bin", "craft.py")] + command)

    def run(self):
        for target, craftDir  in sorted(self.craftRoots.items()):
            commands = self.commands
            if not commands:
                commands = self.config.getSetting("Command", target)
                if commands:
                    commands = [c.strip().split(" ") for c in commands.split(";")]
                if not commands:
                    print("Please specify a command to run.\n"
                          "Either pass -c COMMAND to CraftMaster or set [General]Command in your configuration.")
                    exit(1)
            return self._exec(craftDir, commands)



if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="Craft Master")
    parser.add_argument("--version", action="version", version='%(prog)s 0.1')
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

    master = CraftMaster(args.config, args.commands, args.variables, args.targets)
    if args.print_targets:
        print("Targets:")
        for target in master.targets:
            print("\t", target)
    else:
        exit(master.run())
    exit(0)
