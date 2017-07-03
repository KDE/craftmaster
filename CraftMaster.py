import argparse
import configparser
import os
import shutil
import subprocess

import sys


class CraftMaster(object):
    def __init__(self, configFile, commands, variables):
        self.commands = commands
        self.variables = variables
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
            subprocess.run(["git", "clone", "kde:craft", craftClone], stderr=subprocess.PIPE)
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
        parser = configparser.ConfigParser(interpolation=configparser.ExtendedInterpolation())
        parser.optionxform = lambda option: option
        parser.read(configFile)
        for var in self.variables:
            if not "=" in var:
                print(f"Invalid variable: {var}")
                exit(1)
            key, value = var.split("=", 1)
            parser["Variables"][key] = value
        if not "Root" in parser["Variables"]:
            parser["Variables"]["Root"] = self.defaultWorkDir
        workDir = parser["Variables"]["Root"]
        roots = [root for root in parser.sections() if not root in ["General", "GeneralSettings", "Variables"]]
        if not roots:
            print("Please specify at least one root category")
            exit(0)

        self._init(workDir)

        self._setRoots(workDir, roots)

        if "GeneralSettings" in parser:
            self._setSetting(parser["GeneralSettings"].items())

        for root in roots:
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

    def _setSetting(self, settings, roots=None):
        if not roots:
            roots = self.craftRoots.values()
        for craftDir in roots:
            parser = configparser.ConfigParser()
            ini = os.path.join(craftDir, "etc", "kdesettings.ini")
            if not os.path.isfile(ini):
                parser.read(os.path.join(craftDir, "craft", "kdesettings.ini"))
            else:
                parser.read(ini)
                cache = os.path.join(craftDir, "etc", "cache.pickle")
                if os.path.exists(cache):
                    os.remove(cache)
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

    def _exec(self, args):
        for craftDir  in self.craftRoots.values():
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
    parser.add_argument("--config", action="store", required=True)
    parser.add_argument("--variables", action="store", nargs="+")
    parser.add_argument("-c", "--commands", nargs=argparse.REMAINDER )

    args = parser.parse_args()

    master = CraftMaster(args.config, [args.commands], args.variables or [])
    exit(master.run())
