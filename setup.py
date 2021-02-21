#!/usr/bin/env python3

from setuptools import setup, find_packages


# Primary package version gets set here. This is used for publishing, and once
# installed, `nautobot.__version__` will have this version number.
VERSION = '1.0.0-beta.1'

# Packages/modules to exclude from packaging
PACKAGE_EXCLUDE = [
    "jobs",
    "reports",
    "scripts",
]

# Parse the requirements files
with open('requirements.txt') as fh:
    INSTALL_REQUIRES = fh.read().splitlines()

with open('requirements-dev.txt') as fh:
    DEV_REQUIRES = fh.read().splitlines()

# Parse the README
with open('README.md') as fh:
    README = fh.read()


setup(
    long_description=README,
    name='nautobot',
    version=VERSION,
    python_requires='<4,>=3.6',
    author='Network to Code',
    author_email='opensource@networktocode.com',
    url='https://nautobot.com',
    description='Source of truth and network automation platform.',
    license='Apache-2.0',
    packages=find_packages('nautobot_root', exclude=PACKAGE_EXCLUDE),
    package_dir={"": "nautobot_root"},  # Find packages inside `nautobot_root`
    include_package_data=True,
    package_data={
        "nautobot": [
            "project-static/**",
            "*/templates/**",
        ],
    },
    install_requires=INSTALL_REQUIRES,
    extras_require={
        "dev": DEV_REQUIRES,
    },
    entry_points={
        "console_scripts": [
            "nautobot-server=nautobot.core.cli:main",
        ]
    }
)
