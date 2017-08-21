import configparser
import os


class Config(object):
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


    def getSetting(self, key, target=None, default=None):
        if target:
            section = f"{target}-settings"
            return self.get(section, key, self.get("General", key, default=default))
        return self.get("General", key)


    @property
    def targets(self):
        if not self._targets:
            targets = set(self._config.sections())
            targets -= set(["General", "GeneralSettings", "Variables"])
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


    def get(self, section, key, default=None):
        if default and not (section, key) in self:
            return default
        return self._config.get(section, key)

    def getBool(self, section, key, default=None):
        if default and not (section, key) in self:
            return default
        return self._config.getboolean(section, key)
