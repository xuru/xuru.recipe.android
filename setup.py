from setuptools import setup, find_packages

name = "xuru.recipe.android"
version = '0.8.0'

setup(
    name=name,
    version=version,
    long_description=open('README.md').read(),

    packages=find_packages(exclude=['ez_setup']),
    include_package_data=True,
    zip_safe=True,

    install_requires=['zc.buildout', 'setuptools', 'pexpect'],
    entry_points={'zc.buildout': ['default=%s:Recipe' % name]},

    author="Eric Plaster",
    author_email="plaster@gmail.com",
    description="android zc.buildout recipe",
    license="MIT License",
    url='http://www.python.org/pypi/' + name,

    namespace_packages=['xuru', 'xuru.recipe'],

    classifiers=[
        'Framework :: Buildout',
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Topic :: Software Development :: Build Tools',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ]
)
