
xuru.recipe.android
===================

This recipe allows you to install the android sdk as part of your parts list.

::

    [my_android_sdk]
    recipe = xuru.recipe.android
    apis = 16 17
    system_images = intel mips
    sdk = http://dl.google.com/android/android-sdk_r22.0.1-macosx.zip

This will install the android sdk into the parts directory, and the
following sdk tools will be installed:

- platform-tools
- build-tools
- tools
- extra-android-support
- Any APIs and system images specified.

APIs

- Each API listed in the apis list will install the system image based on the system_images list.

Any other package can be installed by using the "other_packages" parameter.  For
example::

    [my_adroid_sdk]
    recipe = xuru.recipe.android
    apis = 16 17
    system_images = intel mips
    sdk = http://dl.google.com/android/android-sdk_r22.0.1-macosx.zip
    other_packages = 
        Google Play APK Expansion Library
        Google Web Driver

To find what packages are available, run "android list sdk -a" from the
commandline.

Binaries
--------

A script will be generated in the bin directory for each of the following binaries:
- android
- emulator
- uiautomationviewer
- lint
- adb
