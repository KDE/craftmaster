import argparse
import configparser
import os
import shutil
import subprocess

class CraftMaster(object):
    def __init__(self):
        self.craftRoots = {}


    def setRoots(self, craftRoots):
        self.craftRoots = {}
        for root in craftRoots:
            craftRoot = root
            if not os.path.isabs(craftRoot):
                craftRoot = os.path.join(os.getcwd(), craftRoot)
            if not os.path.isfile(os.path.join(craftRoot, "craft", "craftenv.ps1")):
                print(f"Failed to dtect craft in {root}")
                exit(1)
            self.craftRoots[root] = craftRoot

    def setConfig(self, configFile, commands):
        parser = configparser.ConfigParser()
        parser.read(configFile)
        roots = [root for root in parser.sections() if not root in ["General", "GeneralSettings"]]
        print(roots)
        if not roots:
            print("Please specify at least one root category")
            exit(0)

        self.setRoots(roots)


        if "GeneralSettings" in parser:
            self.setSetting(parser["GeneralSettings"].items())

        for root in roots:
            if root in parser:
                self.setSetting(parser[root].items(), [self.craftRoots[root]])

        exit()

        exit()
        if not commands:
            commands = []
            if "ListFile" in parser["General"]:
                listFile = parser["General"]["ListFile"]
                if not os.path.isabs(listFile):
                    listFile = os.path.join(os.getcwd(), listFile)
                commands += ["--list-file", listFile]
            if "Command" in parser["General"]:
                commands += parser["General"]["Command"].split(" ")
            exit(self.run(commands))

    def setSetting(self, settings, roots=None):
        if not roots:
            roots = self.craftRoots.values()
        for craftDir in roots:
            ini = os.path.join(craftDir, "etc", "kdesettings.ini")
            if not os.path.exists(ini):
                shutil.copy(os.path.join(craftDir, "craft", "kdesetings.ini"), ini)
            parser = configparser.ConfigParser()
            parser.read(ini)
            for key, value in settings:
                sectin, key = key.split("/", 1)
                if not sectin in parser:
                    parser.add_section(sectin)
                parser[sectin][key] = value
            with open(ini, 'wt+') as configfile:
                parser.write(configfile)

    def run(self,  args):
        for craftDir  in self.craftRoots.values():
            print(" ".join(args))
            out = subprocess.run(["powershell", "-NoProfile", os.path.join(craftDir, "craft", "craftenv.ps1"), "craft"] + args)
            if not out.returncode == 0:
                return  out.returncode
        return 0



if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--craft-roots", action="store", nargs="*")
    group.add_argument("--master-config", action="store")

    parser.add_argument("-c", "--commands", nargs="*" )

    args = parser.parse_args()

    master = CraftMaster()

    if not args.master_config:
        master.setRoots(args.craft_roots)
    else:
        master.setConfig(args.master_config, args.commands)

    exit(master.run(args.commands))
    parser.print_help()
