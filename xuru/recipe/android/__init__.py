import logging
import os
import sys
import stat
import shutil
import os.path
import zc.buildout
import zc.buildout.download
import setuptools
import subprocess
from android import AndroidPackageManager

template = """#!/bin/bash

export ANDRIOD_HOME={android_home}
{command} $@"""


image_map = {
    'arm': "ARM EABI v7a System Image",
    'intel': "Intel x86 Atom System Image",
    'mips': "MIPS System Image"
}


class Recipe:
    def __init__(self, buildout, name, options):
        self.buildout, self.name, self.options = buildout, name, options
        self.logger = logging.getLogger(name)
        self.mountpoint = None

        root_logger = logging.getLogger()
        self.verbose = root_logger > 10
        self.platform = self._get_platform()

        self.apis = self.options.get('apis', '').split()
        self.images = self.options.get('system_images', '').split()
        self.other_pkgs = self.options.get('other_packages', '').split('\n')

        self.bin_dir = buildout['buildout'].get('bin-directory')
        self.parts_dir = os.path.join(buildout['buildout'].get('parts-directory'), self.name)
        self._setup_install_dirs()

        self.dryrun = True if self.options.get('dryrun', 'false') in ['True', '1', 'true'] else False
        self.force = True if self.options.get('force', 'false') in ['True', '1', 'true'] else False
        self.apm = AndroidPackageManager(self.sdk_dir, logger=self.logger, dryrun=self.dryrun, force=self.force)

        self.logger.info("dryrun: %s" % self.dryrun)
        self.logger.info("force: %s" % self.force)

        self.android = os.path.join(self.sdk_dir, "tools", "android")
        # make sure we have a parts directory
        if not os.path.exists(self.parts_dir):
            os.makedirs(self.parts_dir)

        # build up a list of scripts to generate
        self.sdk_scripts = {}
        for name in ['emulator', 'uiautomatorviewer', 'lint', 'android']:
            self.sdk_scripts[name] = (os.path.join(self.sdk_dir, 'tools', name), os.path.join(self.bin_dir, name))
        self.sdk_scripts['adb'] = (os.path.join(self.sdk_dir, 'platform-tools', 'adb'), os.path.join(self.bin_dir, 'adb'))

        # save off options so other parts can access these values
        buildout[self.name]['sdk_dir'] = self.sdk_dir

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
            raise SystemError("Operating system is not supported: %s" % sys.platform)
        return platform

    def _setup_install_dirs(self):
        self.install_dir = self.options.get('install_dir', None)
        if self.install_dir:
            if not os.path.exists(self.install_dir):
                os.makedirs(self.install_dir)

        if self.install_dir:
            self.sdk_dir = os.path.join(self.install_dir, "android-sdk-" + self.platform)
        else:
            self.sdk_dir = os.path.join(self.parts_dir, "android-sdk-" + self.platform)

    def _remove_scripts(self):
        for _from, _to in self.sdk_scripts.values():
            if os.path.exists(_to):
                self.logger.info("Removing script: %s" % _to)
                os.unlink(_to)

    def _create_scripts(self):
        for _from, _to in self.sdk_scripts.values():
            data = template.format(android_home=self.sdk_dir, command=_from)
            self.logger.info("Creating script: %s" % _to)
            open(_to, "w+").write(data)

            # set the permissions to allow execution
            os.chmod(
                _to,
                os.stat(_to).st_mode | stat.S_IXOTH | stat.S_IXGRP | stat.S_IXUSR)

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

    def _get_mount_point(self):
        if not self.mountpoint:
            output = subprocess.check_output(['/usr/bin/hdiutil', 'info'])
            for line in output.split('\n'):
                if '/Volumes/IntelHAXM' in line:
                    self.mountpoint = line.split('\t')[-1]
        return self.mountpoint

    def _mount_haxm(self):
        if self._get_mount_point():
            self._umount_haxm()

        dmg = os.path.join(self.sdk_dir, 'extras', 'intel', 'Hardware_Accelerated_Execution_Manager', 'IntelHAXM.dmg')
        subprocess.check_output(['/usr/bin/hdiutil', 'mount', dmg])

    def _umount_haxm(self):
        mountpoint = self._get_mount_point()
        subprocess.check_output(['/usr/bin/hdiutil', 'detach', mountpoint])

    def _install_haxm(self, name):
        if not self.apm.is_installed(name):
            self._mount_haxm()

        mpkg = None
        mntpt = self._get_mount_point()
        for f in os.listdir(mntpt):
            if f.endswith('.mpkg'):
                mpkg = os.path.join(mntpt, f)

        if not mpkg:
            raise SystemError("Unable to find installer for IntelHAXM in %s" % mntpt)

        cmd = "sudo installer -pkg %s -target /" % mpkg
        subprocess.call(['/bin/bash', '-c'] + cmd.split(), shell=True)

    def _install_packages(self):
        self.logger.info("Installing packages...")

        # install some required
        self.apm.install('Android SDK Platform-tools', skip_checks=True)
        self.apm.install('Android SDK Tools', skip_checks=True)
        self.apm.install('Android Support Library')

        self.logger.info("Installing other packages...")
        for pkg in self.other_pkgs:
            self.apm.install(pkg)

    def _install_api_packages(self):
        self.logger.info("Installing api packages...")
        for api in self.apis:
            self.apm.install('Android SDK Build-tools', api)
            self.apm.install('SDK Platform', api)
            for image in self.images:
                try:
                    self.apm.install(image_map[image], api)
                except Exception, e:
                    self.logger.error("Error installing image: %s" % e)

    def install(self):
        if not os.path.exists(self.sdk_dir) or self.force:
            self._remove_scripts()
            self._download_install()
        else:
            # seems we already have an sdk?  We probably are doing an update...
            self.logger.info("Android SDK already detected.  Use 'force=True' to override.")

        try:
            self._install_packages()
            self._install_api_packages()
        except OSError, e:
            # It's possible that the install was interupted...  retry from
            # scratch.
            self.logger.warn("OSError installing packages (%s).  Starting over from scratch..." % e)
            shutil.rmtree(self.sdk_dir)
            self._install_packages()
            self._install_api_packages()

        name = "Intel x86 Emulator Accelerator (HAXM)"
        if self._get_platform() == "macosx" and name in self.other_pkgs:
            if not self.apm.is_installed(name):
                self._install_haxm(name)

        self._create_scripts()

        return [_to for _from, _to in self.sdk_scripts.values()]

    def update(self):
        self.apm.update()
