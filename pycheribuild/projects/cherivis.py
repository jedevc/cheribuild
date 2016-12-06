#
# Copyright (c) 2016 Alex Richardson
# All rights reserved.
#
# This software was developed by SRI International and the University of
# Cambridge Computer Laboratory under DARPA/AFRL contract FA8750-10-C-0237
# ("CTSRD"), as part of the DARPA CRASH research programme.
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
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.
#
import os
from pathlib import Path

from ..project import Project
from ..utils import *


def gnuStepInstallInstructions():
    if IS_FREEBSD:
        return "Try running `pkg install gnustep-make gnustep-gui` or `cheribuild.py gnustep` to build from source"
    if IS_LINUX:
        return ("Try running `cheribuild.py gnustep`. It might also be possible to use distribution packages but they"
                " will probably be too old.")
        # packaged versions don't seem to work
        #     osRelease = parseOSRelease()
        #     print(osRelease)
        #     if osRelease["ID"] == "ubuntu":
        #         return """Somehow install GNUStep"""
        #     elif osRelease["ID"] == "opensuse":
        #         return """Try installing gnustep-make from the X11:/GNUstep project:
        # sudo zypper addrepo http://download.opensuse.org/repositories/X11:/GNUstep/openSUSE_{OPENSUSE_VERSION}/ gnustep
        # sudo zypper in libobjc2-devel gnustep-make gnustep-gui-devel gnustep-base-devel""".format(OPENSUSE_VERSION=osRelease["VERSION"])


class BuildCheriVis(Project):
    dependencies = ["cheritrace"]
    repository = "https://github.com/CTSRD-CHERI/CheriVis.git"

    # TODO: allow external cheritrace
    def __init__(self, config: CheriConfig):
        super().__init__(config, installDir=config.sdkDir, appendCheriBitsToBuildDir=True)
        self._addRequiredSystemTool("clang")
        self._addRequiredSystemTool("clang++")
        if IS_LINUX or IS_FREEBSD:
            self._addRequiredSystemTool("gnustep-config", installInstructions=gnuStepInstallInstructions)
        else:
            fatalError("Build currently only supported on Linux or FreeBSD!")
        self.gnustepMakefilesDir = None  # type: Path
        self.makeCommand = "make" if IS_LINUX else "gmake"

    def checkSystemDependencies(self):
        super().checkSystemDependencies()
        configOutput = runCmd("gnustep-config", "--variable=GNUSTEP_MAKEFILES", captureOutput=True).stdout
        self.gnustepMakefilesDir = Path(configOutput.decode("utf-8").strip())
        commonDotMake = self.gnustepMakefilesDir / "common.make"
        if not commonDotMake.is_file():
            self.dependencyError("gnustep-config binary exists, but", commonDotMake, "does not exist!",
                                 installInstructions=gnuStepInstallInstructions())
        # has to be a relative path for some reason....
        # pathlib.relative_to() won't work if the prefix is not the same...
        expectedCheritraceLib = str(self.config.sdkDir / "lib/libcheritrace.so")
        cheritraceLib = Path(os.getenv("CHERITRACE_LIB") or expectedCheritraceLib)
        if not cheritraceLib.exists():
            fatalError(cheritraceLib, "does not exist", fixitHint="Try running `cheribuild.py cheritrace` and if that"
                       " doesn't work set the environment variable CHERITRACE_LIB to point to libcheritrace.so")
            return
        cheritraceDirRelative = os.path.relpath(str(cheritraceLib.parent.resolve()), str(self.sourceDir.resolve()))
        # TODO: set ADDITIONAL_LIB_DIRS?
        # http://www.gnustep.org/resources/documentation/Developer/Make/Manual/gnustep-make_1.html#SEC17
        # http://www.gnustep.org/resources/documentation/Developer/Make/Manual/gnustep-make_1.html#SEC29

        # library combos:
        # http://www.gnustep.org/resources/documentation/Developer/Make/Manual/gnustep-make_1.html#SEC35

        self.commonMakeArgs.extend([
            "CXX=clang++", "CC=clang",
            "GNUSTEP_MAKEFILES=" + str(self.gnustepMakefilesDir),
            "CHERITRACE_DIR=" + cheritraceDirRelative,  # make it find the cheritrace library
            "GNUSTEP_INSTALLATION_DOMAIN=USER",
            "GNUSTEP_NG_ARC=1",
            "messages=yes",
        ])

    def clean(self):
        # doesn't seem to be possible to use a out of source build
        self.runMake(self.commonMakeArgs, "clean", cwd=self.sourceDir)

    def compile(self):
        self.runMake(self.commonMakeArgs, "print-gnustep-make-help", cwd=self.sourceDir)
        self.runMake(self.commonMakeArgs, "all", cwd=self.sourceDir)

    def install(self):
        self.runMake(self.commonMakeArgs, "install", cwd=self.sourceDir)

#
# Some of these settings seem required:
"""
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>GSAllowWindowsOverIcons</key>
    <integer>1</integer>
    <key>GSAppOwnsMiniwindow</key>
    <integer>0</integer>
    <key>GSBackHandlesWindowDecorations</key>
    <integer>0</integer>
    <key>GSUseFreedesktopThumbnails</key>
    <integer>1</integer>
    <key>GraphicCompositing</key>
    <integer>1</integer>
    <key>NSInterfaceStyleDefault</key>
    <string>NSWindows95InterfaceStyle</string>
    <key>NSMenuInterfaceStyle</key>
    <string>NSWindows95InterfaceStyle</string>
</dict>
</plist>
"""
#
