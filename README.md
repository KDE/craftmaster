Craft Master
============
Orchestrate multiple [Craft](https://cgit.kde.org/craft.git/) configurations.

The following configuration has a basic configuration based on ```[GeneralSettings]``` and seperate settings for ```[msvc2015x86],[msvc2015x64]``` and ```[mingw]```.

For each one a seperate directory will be created and the commands will be executed on each of them.


    # Avalible variables are
    # Variables:Root: Root is defined relative to CraftMaster and points to the subdirectory work
    [General]
    Command=-p quassel; nsis; --install-deps quassel
    Branch = master
    ShallowClone = True

    # Variables defined here override the default value
    # The variable names are casesensitive
    [Variables]
    #Root = D:\qt-sdk

    #Values need to be overwritten to create a chache
    UseCache = True
    CreateCache = False
    Ignores = dev-util/perl
    Msys = C:\msys64\

    # Settings applicable for all Crafts matrices
    # Settings are Category/key=value
    # Category is case sensitive

    [GeneralSettings]
    Paths/python = C:\Python36
    Paths/python27 = C:\Python27
    Paths/downloaddir = ${Variables:Root}\downloads
    Paths/Msys = ${Variables:Msys}
    ShortPath/emerge_use_short_path = False
    Packager/CacheDir = ${Variables:Root}\cache
    Packager/UseCache = ${Variables:UseCache}
    Packager/CreateCache = ${Variables:CreateCache}
    Packager/RepositoryUrl = https://files.kde.org/craft/
    Compile/BuildType = Release
    ContinuousIntegration/Enabled = True
    QtSDK/Version = 5.9
    QtSDK/Path = C:\Qt
    QtSDK/Enabled = True
    Portage/Ignores = ${Variables:Ignores};win32libs/icu;binary/mysql;win32libs/dbus
    CraftDebug/DumpSettings = True
    PortageVersions/kf5 = 5.35.0
    PortageVersions/KDEApplications = 17.04.2
    PortageVersions/qt-apps/quassel = master

    [msvc2015x86]
    QtSDK/Compiler = msvc2015
    General/KDECompiler = msvc2015
    General/Architecture = x86

    [msvc2015x64]
    QtSDK/Compiler = msvc2015_64
    General/KDECompiler = msvc2015
    General/Architecture = x64

    [mingw]
    QtSDK/Compiler = mingw53_32
    General/KDECompiler = mingw4
    General/Architecture = x86


