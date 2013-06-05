import logging
import os
import sys
import stat
import os.path
import zc.buildout
import zc.buildout.download
import setuptools
import pexpect
import subprocess

template = """#!/bin/bash

export ANDRIOD_HOME={android_home}
{command} $@"""


class Recipe:
    def __init__(self, buildout, name, options):
        self.buildout, self.name, self.options = buildout, name, options
        self.logger = logging.getLogger(name)

        # determine platform string to use
        if sys.platform.startswith('linux'):
            self.platform = 'linux'
        elif sys.platform.startswith('darwin'):
            self.platform = 'macosx'
        elif sys.platform.startswith('win32'):
            self.platform = 'windows'
        else:
            raise SystemError("Can't guess your platform")

        self._setup_paths(buildout)

        self.install_cmd = [
            os.path.join(self.sdk_dir, 'tools', 'android'),
            '-v', 'update', 'sdk', '-s', '-u']

        if 'dry-run' in options:
            self.install_cmd.append('--dry-mode')

    def _setup_paths(self, buildout):
        self.download_cache = buildout['buildout'].get('download-cache')
        self.parts_dir = os.path.join(buildout['buildout'].get('parts-directory'), self.name)
        self.bin_dir = buildout['buildout'].get('bin-directory')

        self.sdk_dir = os.path.join(self.parts_dir, "android-sdk-" + self.platform)
        self.target_install = os.path.join(self.bin_dir, self.name)

        self.sdk_script_binaries = []
        for name in ['android', 'emulator', 'uiautomatorviewer', 'lint']:
            self.sdk_script_binaries.append(os.path.join(self.sdk_dir, 'tools', name))

        self.sdk_script_binaries.append(os.path.join(self.sdk_dir, 'platform-tools', 'adb'))

    def _get_not_installed(self):
        env = os.environ
        env['ANDROID_HOME'] = self.sdk_dir
        cmd = os.path.join(self.sdk_dir, 'tools', 'android')

        self.not_installed = {}
        output = subprocess.check_output([cmd, 'list', 'sdk'], env=env)
        for line in output.split('\n'):
            if '- ' in line:
                index, desc = [x.strip() for x in line.split('- ')]
                self.not_installed[index] = desc

    def _calculate_packages(self):
        apis = self.options.get('apis', '').split()
        images = self.options.get('images', '').split()
        google_apis = self.options.get('google_apis')
        others = self.options.get('other_packages', '').split('\n')

        installables = []
        for index, line in self.not_installed.items():
            # required...
            if 'Android SDK Tools' in line:
                installables.append(index)
            elif 'Android SDK Platform-tools' in line:
                installables.append(index)
            elif 'Android SDK Build-tools' in line:
                installables.append(index)
            elif 'Android Support Library' in line:
                installables.append(index)

            elif 'SDK Platform Android' in line:
                for api in apis:
                    if 'API ' + api in line:
                        installables.append(index)

            elif 'System Image' in line:
                for image in images:
                    for api in apis:
                        if 'API ' + api in line:
                            if image.lower() == 'arm' and 'ARM EABI v7a' in line:
                                installables.append(index)
                            elif image.lower() == 'intel' and 'Intel x86 Atom' in line:
                                installables.append(index)
                            elif image.lower() == 'mips' and 'MIPS' in line:
                                installables.append(index)

            elif 'Google APIs' in line and google_apis:
                for api in apis:
                    if 'API ' + api in line:
                        installables.append(index)

            for other in others:
                if other in line:
                    installables.append(index)

        return installables

    def _install_tool(self, tool):
        self.logger.info("Installing android: %s" % tool)
        cmd = self.install_cmd + ['-t', tool]

        env = os.environ
        env['ANDROID_HOME'] = self.sdk_dir

        child = pexpect.spawn(" ".join(cmd), logfile=sys.stdout, env=env)
        already_installed = 'Warning: The package filter removed all packages'

        done = False
        while not done:
            index = child.expect(['\[y\/n\]', already_installed, pexpect.EOF, pexpect.TIMEOUT])
            if index == 0:
                child.sendline('y')
            elif index == 1:
                done = True
            elif index == 2:
                done = True
        if child.isalive():
            child.wait()

        if 'Intel x86 Emulator Accelerator' in self.not_installed[tool]:
            self.logger.warn("*" * 80)
            self.logger.warn("Be sure to install ")
            self.logger.warn("parts/android/android-sdk-macosx/extras/intel/Hardware_Accelerated_Execution_Manager/IntelHAXM.dmg")
            self.logger.warn("before using the emulator.")
            self.logger.warn("*" * 80)

    def _create_script(self, cmd, env=os.environ):
        data = template.format(android_home=self.sdk_dir, command=cmd)
        script_fn = os.path.join(self.bin_dir, os.path.split(cmd)[-1])
        open(script_fn, "w+").write(data)

        # set the permissions to allow execution
        os.chmod(
            script_fn,
            os.stat(script_fn).st_mode | stat.S_IXOTH | stat.S_IXGRP | stat.S_IXUSR)

    def build(self):
        self.logger.info('installing tools')

        if os.path.exists(self.target_install):
            os.unlink(self.target_install)

        url = self.options['sdk']

        filename = os.path.join('downloads', url.split('/')[-1])

        # download the sdk
        download = zc.buildout.download.Download(
            self.buildout['buildout'], namespace=self.name, hash_name=True,
            logger=self.logger)
        filename, is_temp = download(url)

        # now unpack it
        self.logger.info('Unpacking and configuring')
        try:
            setuptools.archive_util.unpack_archive(filename, self.parts_dir)
        finally:
            if is_temp:
                os.remove(filename)

        # now get what isn't installed...
        self._get_not_installed()

        for package in self._calculate_packages():
            if 'System Image, Android API 17' in self.not_installed[package]:
                if not os.path.exists(os.path.join(self.parts_dir, '.installed_api17')):
                    self._install_tool(package)
            else:
                self._install_tool(package)

            # work around for the latest android not returning the correct
            # information...  android list sdk will always list the system
            # images for api 17...
            if 'System Image, Android API 17' in self.not_installed[package]:
                open(os.path.join(self.parts_dir, '.installed_api17'), 'w+').write('true')

        for script in self.sdk_script_binaries:
            self._create_script(script)

    def install(self):
        # -a will force a re-install
        #self.install_cmd.append('-a')
        self.build()
        return ['bin/%s' % self.name]

    def update(self):
        self.build()
