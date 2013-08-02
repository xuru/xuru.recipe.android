Changelog
=========

0.10.0 - 2013-08-02
-------------------
* Rewrote everything to inspect the file system instead of relying on the android app to tell use what needs installing and what doesn't.
* Fixed verbose settings: -vv for verbose -vvvv to see the license agreements
* Added two settings: "dryrun" and "force"
* Corrected script generation (and now correctly detects if something isn't
  installed based on those).
* Fixed install order for dependencies.
* Now much more consistant.

0.9.1 - Unreleased
------------------

* Nothing yet...

0.9.0 - 2013-06-12
------------------

* Cleaned up the source code.
* Now sets the buildout variable for the sdk_dir that other parts can access
  like ${android:sdk_dir}
* Added support for verboseness

0.8.9 - 2013-06-11
------------------

* Fixed an error that caused it to never exit the install loop if the api 17
  image was being installed, and other packages after that one.
* Terminates the child when it times out after 30 seconds.

0.8.8 - 2013-06-10
------------------

* Added new option ``install_dir`` to install it in a seperate directory other
  then the parts directory.

0.8.7 - 2013-06-05
------------------

* Rewrote how it finds packages and installs them.

0.8.6 - 2013-06-05
------------------

* Initial push to pypi
