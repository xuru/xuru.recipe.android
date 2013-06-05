from setuptools import setup, find_packages
import os

name = "xuru.recipe.android"
version = '0.8.7'


def read(*pathnames):
    return open(os.path.join(os.path.dirname(__file__), *pathnames)).read()


setup(
    name=name,
    version=version,
    long_description=read('README.rst'),

    packages=find_packages(exclude=['ez_setup']),
    package_data={'xuru.recipe': ['android/*.rst']},
    include_package_data=True,
    zip_safe=True,

    install_requires=['zc.buildout', 'setuptools', 'pexpect'],
    entry_points={'zc.buildout': ['default=%s:Recipe' % name]},

    author="Eric Plaster",
    author_email="plaster@gmail.com",
    description="android zc.buildout recipe",
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
