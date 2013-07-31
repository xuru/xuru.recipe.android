
from glob import glob
import logging
import re
import sys
import os
import os.path
import subprocess
import pexpect

package_regex = re.compile("(?P<index>\d+)[-] (?P<title>.*), (?P<revision>.*)")
api_regex = re.compile("(?P<index>\d+)[-] (?P<title>.*), (?P<api>.*), (?P<revision>.*)")

installed_package_checks = {
    'Android SDK Tools': 'tools/lib/rule-api.jar',
    'Android SDK Platform-tools': 'platform-tools',
    'Android Support Library': 'extras/android/support',
    'Android Support Repository': 'extras/android/m2repository',
    'Google AdMob Ads SDK': 'extras/google/admob_ads_sdk',
    'Google Analytics App Tracking SDK': 'extras/google/analytics_sdk_v2',
    'Google Play services': 'extras/google/google_play_services',
    'Google Repository': 'extras/google/m2repository',
    'Google Play APK Expansion Library': 'extras/google/play_apk_expansion',
    'Google Play Billing Library': 'extras/google/play_billing',
    'Google Play Licensing Library': 'extras/google/play_licensing',
    'Google Web Driver': 'extras/google/webdriver',
    'Documentation for Android SDK': 'docs',
    'Intel x86 Emulator Accelerator (HAXM)': '/System/Library/LaunchDaemons/com.intel.haxm.plist',
    'Android SDK Build-tools': 'build-tools/%s*'
}

installed_api_checks = {
    'Samples for SDK': 'samples/android-%s',
    'SDK Platform': 'platforms/android-%s/android.jar',
    'ARM EABI v7a System Image': 'system-images/android-%s/armeabi-v7a',
    'Intel x86 Atom System Image': 'system-images/android-%s/x86',
    'MIPS System Image': 'system-images/android-%s/mips',
    'Google APIs': 'add-ons/addon-google_apis-google-%s',
    'Sources for Android SDK': 'sources/android-%s'
}


class AndroidPackageManager(object):
    def __init__(self, sdk_dir=None, logger=None, verbose=10, dryrun=False, force=False):
        self.logger = logger
        self.sdk_dir = sdk_dir
        self.verbose = verbose > 10
        self.show_output = verbose > 20
        self.dryrun = dryrun
        self.force = force

        if not sdk_dir:
            if not 'ANDROID_HOME' in os.environ:
                raise Exception("Unable to find Android SDK")
            else:
                self.sdk_dir = os.environ['ANDROID_HOME']

        if not logger:
            self.logger = logging.getLogger('xuru.recipe.android.apm')

        self.apis = {}
        self.packages = {}

    def _parse_package_line(self, line):
        groups = package_regex.search(line).groupdict()
        if groups['revision'].startswith('revision'):
            groups['revision'] = groups['revision'].split(' ')[-1]
        return groups

    def _parse_api_line(self, line):
        groups = api_regex.search(line).groupdict()
        if groups['api'].startswith('Android API') or groups['api'].startswith('API '):
            groups['api'] = groups['api'].split(' ')[-1]

        if groups['title'].startswith('SDK Platform Android'):
            groups['title'] = 'SDK Platform'

        return groups['api'], {'title': groups['title'], 'revision': groups['revision'], 'index': groups['index']}

    def _read_data(self):
        cmd = [
            os.path.join(self.sdk_dir, 'tools', 'android'), 'list', 'sdk', '-a']
        output = subprocess.check_output(cmd)
        return [x.strip() for x in output.split('\n')]

    def _update_api_list(self, api, groups):
        if api not in self.apis:
            self.apis[api] = {}
        self.apis[api][groups['title']] = groups

    def _update_package_list(self, groups):
        if groups['title'].startswith('Samples for SDK'):
            api = groups['title'].split()[-1]
            groups['title'] = 'Samples for SDK'
            self._update_api_list(api, groups)
        else:
            title = groups['title']

            if title in self.packages:
                if isinstance(self.packages[title], list):
                    self.packages[title].append(groups)
                else:
                    self.packages[title] = [self.packages[title], groups]
            else:
                self.packages[title] = groups

    def package_list(self):
        lines = self._read_data()

        found = False
        for line in lines:
            if line.startswith('Packages available for installation or update'):
                found = True
                continue

            if not found or not line:
                continue

            if line.count(',') == 1:
                groups = self._parse_package_line(line)
                self._update_package_list(groups)

            elif line.count(',') == 2:
                api, data = self._parse_api_line(line)
                self._update_api_list(api, data)

    def _android_update(self, additional_cmds=[], env=os.environ):
        cmd = [os.path.join(self.sdk_dir, 'tools', 'android')]
        cmd += ['-s']
        cmd += ['update', 'sdk', '-u']
        cmd += additional_cmds
        if self.dryrun:
            cmd.append('--dry-mode')

        env['ANDROID_HOME'] = self.sdk_dir

        logfile = None
        if self.show_output:
            logfile = sys.stdout

        def acknowledge(d):
            d['child'].sendline('y')

        pexpect.run(" ".join(cmd), events={'\[y\/n\]': acknowledge}, logfile=logfile,
                    env=env, timeout=60)

    def is_installed(self, name, api=None):
        if name in installed_package_checks:
            return self.check(name, api, installed_package_checks)
        else:
            return self.check(name, api, installed_api_checks)

    def check(self, name, api, installed_checks):
        filepath = os.path.join(self.sdk_dir, installed_checks[name])

        if '%s' in filepath:
            filepath = filepath % api

        if '*' in filepath:
            filelist = glob(filepath)
            if filelist:
                filepath = filelist[0]

        if self.verbose:
            self.logger.info("  Checking for: %s" % filepath)

        return os.path.exists(filepath)

    def install_package(self, name, api, skip_checks=False):
        installed = self.check(name, api, installed_package_checks)
        if installed and not skip_checks:
            self.logger.info("  Already installed: %s [%s]" % (name, api))

        else:
            # An exception...  Android SDK Build-tools, doesn't exist
            # before API 17
            if name == "Android SDK Build-tools" and int(api) < 17:
                self.logger.info("  Skipping %s API %s as it is pre API 17" % (name, api))
                return

            self.logger.info("Installing %s" % name)

            if isinstance(self.packages[name], list):
                for pkg in self.packages[name]:
                    self._android_update(additional_cmds=['-a', '-t', pkg['index']])
            else:
                self._android_update(
                    additional_cmds=['-a', '-t', self.packages[name]['index']])

    def install_api_package(self, name, api, skip_checks=False):
        installed = self.check(name, api, installed_api_checks)
        if installed and not skip_checks:
            self.logger.info("  Already installed: %s [%s]" % (name, api))
        else:
            self.logger.info("Installing %s [API %s]" % (name, api))
            self._android_update(
                additional_cmds=['-a', '-t', self.apis[api][name]['index']])

    def install(self, name, api=None, skip_checks=False):
        """ installs/updates a specific package """
        if not self.packages:
            self.package_list()

        if name in installed_package_checks:
            self.install_package(name, api, skip_checks)
        elif name in installed_api_checks:
            self.install_api_package(name, api, skip_checks)
        else:
            self.logger.error("ERROR: Unable to install %s.  Please check the package name." % name)

    def update(self):
        """ Updates all packages """
        if not self.packages:
            self.package_list()

        self._android_update()
