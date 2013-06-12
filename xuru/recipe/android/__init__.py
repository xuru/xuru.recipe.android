import logging
import os
import re
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


image_map = {
    'arm': "ARM EABI v7a",
    'intel': "Intel x86 Atom",
    'mips': "MIPS"
}


class Recipe:
    def __init__(self, buildout, name, options):
        self.buildout, self.name, self.options = buildout, name, options
        self.logger = logging.getLogger(name)

        self.platform = self._get_platform()
        self.apis = self.options.get('apis', '').split()
        self.images = self.options.get('system_images', '').split()
        self.bin_dir = buildout['buildout'].get('bin-directory')
        self.parts_dir = os.path.join(buildout['buildout'].get('parts-directory'), self.name)
        self.sdk_dir = self._get_install_dir()

        # save off options so other parts can access these values
        options['sdk_dir'] = self.sdk_dir
        options['parts_dir'] = self.parts_dir
        options['images'] = self.images
        options['apis'] = self.apis

        # make sure we have a parts directory
        if not os.path.exists(self.parts_dir):
            os.makedirs(self.parts_dir)

        # build up a list of scripts to generate
        self.sdk_script_binaries = []
        for name in ['emulator', 'uiautomatorviewer', 'lint']:
            self.sdk_script_binaries.append(os.path.join(self.sdk_dir, 'tools', name))
        self.sdk_script_binaries.append(os.path.join(self.sdk_dir, 'platform-tools', 'adb'))

        # install command
        self.install_cmd = [
            os.path.join(self.sdk_dir, 'tools', 'android'),
            '-v', 'update', 'sdk', '-s', '-u']

        if 'dry-run' in options:
            self.install_cmd.append('--dry-mode')

    def _get_platform(self):
        platform = None
        # determine platform string to use
        if sys.platform.startswith('linux'):
            platform = 'linux'
        elif sys.platform.startswith('darwin'):
            platform = 'macosx'
        elif sys.platform.startswith('win32'):
            platform = 'windows'
        else:
            raise SystemError("Can't guess your platform")
        return platform

    def _get_install_dir(self):
        install_dir = self.options.get('install_dir', None)
        if install_dir:
            if not os.path.exists(install_dir):
                os.makedirs(install_dir)

            sdk_dir = os.path.join(install_dir, "android-sdk-" + self.platform)
        else:
            sdk_dir = os.path.join(self.parts_dir, "android-sdk-" + self.platform)
        return sdk_dir

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

    def _find_apis(self):
        rv = []
        for api in self.apis:
            regex = re.compile("SDK Platform Android .* API " + api)
            for index, line in self.not_installed.items():
                if regex.search(line):
                    rv.append(index)
        return rv

    def _find_images(self):
        rv = []
        for api in self.apis:
            if api == "17" and os.path.exists(os.path.join(self.parts_dir, '.installed_api17')):
                # we already installed it...
                continue

            for image in self.images:
                regex = re.compile(image_map[image.lower()] + " System Image.*API " + api)
                for index, line in self.not_installed.items():
                    if regex.search(line):
                        rv.append(index)
        return rv

    def _find_required(self):
        rv = []
        for index, line in self.not_installed.items():
            if 'Android SDK Tools' in line:
                rv.append(index)
            elif 'Android SDK Platform-tools' in line:
                rv.append(index)
            elif 'Android SDK Build-tools' in line:
                rv.append(index)
        return rv

    def _calculate_packages(self):
        self._get_not_installed()
        others = self.options.get('other_packages', '').split('\n')

        installables = self._find_required()
        installables += self._find_apis()
        installables += self._find_images()

        for other in others:
            for index, line in self.not_installed.items():
                if other in line:
                    installables.append(index)

        return installables

    def _install_tool(self, tool):
        self.logger.info("Installing android: %s" % self.not_installed[tool])
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
            elif index in [1, 2]:
                done = True
            elif index == 3:
                child.terminate(force=True)
                done = True
        if child.isalive():
            child.wait()

    def _create_script(self, cmd, env=os.environ):
        data = template.format(android_home=self.sdk_dir, command=cmd)
        script_fn = os.path.join(self.bin_dir, os.path.split(cmd)[-1])
        open(script_fn, "w+").write(data)

        # set the permissions to allow execution
        os.chmod(
            script_fn,
            os.stat(script_fn).st_mode | stat.S_IXOTH | stat.S_IXGRP | stat.S_IXUSR)

    def _install(self):
        self.logger.info('installing tools')

        for script in self.sdk_script_binaries:
            if os.path.exists(script):
                os.unlink(script)

        self._download_install()
        self._create_script(os.path.join(self.sdk_dir, "tools", "android"))
        self._update()

    def _download_install(self):
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
            setuptools.archive_util.unpack_archive(filename, self.install_dir)
        finally:
            if is_temp:
                os.remove(filename)
        self._update()

    def _get_next_install_package(self, packages):
        package = packages[0]

        # work around for the latest android not returning the correct
        # information...  android list sdk will always list the system
        # images for api 17...
        if 'System Image, Android API 17' in self.not_installed[package]:

            # we have haven't installed it yet...
            if not os.path.exists(os.path.join(self.sdk_dir, '.installed_api17')):
                open(os.path.join(self.sdk_dir, '.installed_api17'), 'w+').write('true')
                return package

            # we installed it, but there are more packages after it in the list...
            elif len(packages) > 1:
                return packages[1]

            # we installed it, and there are no other packages
            else:
                return None
        else:
            # package isn't api 17, so install it
            return package

    def _update(self):
        done = False

        while not done:
            # we need to do this every time we install something because the
            # numbering will be different
            packages = self._calculate_packages()
            if packages:
                package = self._get_next_install_package(packages)
                if package:
                    self._install_tool(package)
                else:
                    done = True
            else:
                done = True

        for script in self.sdk_script_binaries:
            self._create_script(script)

    def install(self):
        self._install()

        self.logger.warn("*" * 80)
        self.logger.warn("If you installed the Intel x86 Emulator Accelerator package, you will find the installer in")
        self.logger.warn("parts/android/android-sdk-macosx/extras/intel/Hardware_Accelerated_Execution_Manager/IntelHAXM.dmg")
        self.logger.warn("*" * 80)

        return self.sdk_script_binaries

    def update(self):
        self._update()
