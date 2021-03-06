from setuptools import setup, find_packages
import os
import os.path

name = "xuru.recipe.android"
version = '0.10.0'


def read(*pathnames):
    return open(os.path.join(os.path.dirname(__file__), *pathnames)).read()


setup(
    name=name,
    version=version,
    description="A zc.buildout recipe that will install the android sdk and install tools, apis, and images",
    long_description=read('README.rst') + "\n\n" + read(os.path.join("docs", "HISTORY.rst")),

    packages=find_packages(exclude=['ez_setup']),
    package_data={'xuru.recipe': ['android/*.rst']},
    include_package_data=True,
    zip_safe=True,

    install_requires=['zc.buildout', 'setuptools', 'pexpect'],
    entry_points={'zc.buildout': ['default=%s:Recipe' % name]},

    author="Eric Plaster",
    author_email="plaster@gmail.com",
    license="MIT License",
    url='https://github.com/xuru/xuru.recipe.android',

    namespace_packages=['xuru', 'xuru.recipe'],

    keywords='android buildout',
    classifiers=[
        'Framework :: Buildout',
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Topic :: Software Development :: Build Tools',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ]
)
