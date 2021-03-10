#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""The setup.py file."""

import os
from setuptools import setup
from setuptools.command.install import install
import sys

VERSION = "0.3.7"

with open("README.md", "r") as fh:
    long_description = fh.read()


class VerifyVersionCommand(install):
    """Custom command to verify that the git tag matches our version."""

    description = "verify that the git tag matches our version"

    def run(self):
        tag = os.getenv("CIRCLE_TAG")

        if tag != VERSION:
            info = "Git tag: {0} does not match the version of this app: {1}".format(
                tag, VERSION
            )
            sys.exit(info)


setup(
    name="evohome-async",
    version=VERSION,
    author="Andrew Stock & David Bonnes",
    author_email="zxdavb@bonnes.me",
    description="An async Python client for connecting to the Evohome webservice",
    keywords=["evohome", "total connect comfort", "round thermostat"],
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/zxdavb/evohome-async/",
    download_url="https://github.com/zxdavb/evohome-async/tarball/" + VERSION,
    license="Apache 2",
    packages=["evohomeasync", "evohomeasync2"],
    install_requires=["aiohttp"],
    cmdclass={
        "verify": VerifyVersionCommand,
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Development Status :: 5 - Production/Stable",
    ],
)
