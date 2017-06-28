import argparse
import configparser
import os
import shutil
import subprocess

class CraftMaster(object):
    def __init__(self, configFile, commands):
        self.commands = commands
        self._init()
        self._setConfig(configFile)
        # update craft and clear cahces
        self._exec(["craft"])



    def _init(self):
        if not subprocess.getoutput("git config --global --get url.git://anongit.kde.org/.insteadof") == "kde:":
            subprocess.run(["git", "config", "--global", "url.git://anongit.kde.org/.insteadOf", "kde:"])
            subprocess.run(["git", "config", "--global", "url.ssh://git@git.kde.org/.pushInsteadOf", "kde:"])
            subprocess.run(["git", "config", "--global", "core.autocrlf", "false"])
            subprocess.run(["git", "config", "--system", "core.autocrlf", "false"])
        craftClone = os.path.join(os.getcwd(), "craft-clone")
        if not os.path.exists(craftClone):
            subprocess.run(["git", "clone", "kde:craft", craftClone])



    def _setRoots(self, craftRoots):
        self.craftRoots = {}
        for root in craftRoots:
            craftRoot = os.path.join(os.getcwd(), root)
            if not os.path.isdir(craftRoot):
                os.makedirs(os.path.join(craftRoot, "etc"))
            if not os.path.isfile(os.path.join(craftRoot, "craft", "craftenv.ps1")):
                subprocess.run(["cmd", "/C", "mklink", "/J", os.path.join(craftRoot, "craft"), os.path.join(os.getcwd(), "craft-clone")])
            self.craftRoots[root] = craftRoot

    def _setConfig(self, configFile):
        parser = configparser.ConfigParser(interpolation=configparser.ExtendedInterpolation())
        parser.optionxform = lambda option: option
        parser.read(configFile)
        roots = [root for root in parser.sections() if not root in ["General", "GeneralSettings", "Variables"]]
        if not roots:
            print("Please specify at least one root category")
            exit(0)

        self._setRoots(roots)

        if "GeneralSettings" in parser:
            self._setSetting(parser["GeneralSettings"].items())

        for root in roots:
            if root in parser:
                self._setSetting(parser[root].items(), [self.craftRoots[root]])

        if not self.commands:
            self.commands = []
            if "ListFile" in parser["General"]:
                listFile = parser["General"]["ListFile"]
                if listFile:
                    if not os.path.isabs(listFile):
                        listFile = os.path.join(os.getcwd(), listFile)
                    self.commands += ["--list-file", listFile]
            if "Command" in parser["General"]:
                command = parser["General"]["Command"]
                if command:
                    self.commands += command.split(" ")

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
            print(" ".join(args))
            out = subprocess.run(["powershell", "-NoProfile", os.path.join(craftDir, "craft", "craftenv.ps1"), "craft"] + args)
            if not out.returncode == 0:
                return  out.returncode
        return 0

    def run(self):
        return self._exec(self.commands)



if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", action="store", required=True)

    parser.add_argument("-c", "--commands", nargs=argparse.REMAINDER )

    args = parser.parse_args()

    master = CraftMaster(args.config, args.commands)
    exit(master.run())