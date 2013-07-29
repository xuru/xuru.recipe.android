.. contents:: :depth: 1

Introduction
============

**xuru.recipe.android** allows you to install the android sdk as part of your parts list.
For example::

    [my_android_sdk]
    recipe = xuru.recipe.android
    apis = 16 17
    system_images = intel mips
    sdk = http://dl.google.com/android/android-sdk_r22.0.4-macosx.zip
    other_packages = 
        Google Play APK Expansion Library
        Google Web Driver

This will install the android sdk into the parts directory, along with
platform-tools, build-tools, and tools.  It will then install version
16 and 17 apis.  In addition, it will install the intel and mips system images
for each of those apis.

The format of entries in the buidout section (my_android_sdk in this example)
is::

    [section_name]
    recipe = xuru.recipe.android

Where options are:

``apis``
    The list of api versions on one line seperated by spaces.

``system_images``
    The list of system images types for each of the apis specified above.  Valid
    values are intel, mips or arm.

``sdk``
    The full url to the downloadable zip file for the android sdk.

``install_dir``
    Optional absolute directory to install the sdk instead of the default <buidout parts
    directory>/android

``other_packages``
    Optional list (on seperate lines) of extra packages to install.  To see what
    packages there are to install type ``android list sdk -a`` on the command
    line after the sdk has been installed.  The name must be a unique sub-string
    of the names listed.

``dryrun``
    Set this to any of True, False, true, false, 1, 0 to set the boolean value.
    This determines whether or not to include the command line switch
    --dry-mode.

``force``
    Set this to any of True, False, true, false, 1, 0 to set the boolean value.
    Forces replacement of a package or its parts, even if something has been modified. 

Binaries Installed
------------------

A script will be generated in the bin directory for each of the following binaries:
- adb
- android
- emulator
- uiautomationviewer
- lint

What This Does Not Install
--------------------------

If you installed the **Intel x86 Emulator Accelerator (HAXM)** package, you will 
find the installer in:

``parts/android/android-sdk-macosx/extras/intel/Hardware_Accelerated_Execution_Manager/IntelHAXM.dmg``

This recipe will not run any installers at this time.
