#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
"""The setup.py file."""

import os
import sys

from setuptools import find_packages, setup
from setuptools.command.install import install


class VerifyVersionCommand(install):
    """Custom command to verify that the git tag matches our VERSION."""

    def run(self):
        tag = os.getenv("CIRCLE_TAG")
        if tag != VERSION:
            info = "Git tag: {tag} does not match the version of this pkg: {VERSION}"
            sys.exit(info)


VERSION = "0.3.8"


with open("README.md", "r") as fh:
    LONG_DESCRIPTION = fh.read()


setup(
    name="evohome-async",
    description="An async client for connecting to Honeywell's TCC RESTful API.",
    keywords=["evohome", "total connect comfort", "round thermostat"],
    author="Andrew Stock & David Bonnes",
    author_email="zxdavb@bonnes.me",
    url="https://github.com/zxdavb/evohome-async",
    download_url="{url}/archive/{VERSION}.tar.gz",
    install_requires=[list(val.strip() for val in open("requirements.txt"))],
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    packages=find_packages(exclude=["test", "docs"]),
    version=VERSION,
    license="Apache 2",
    python_requires=">=3.7",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3.7",
        "Topic :: Home Automation",
    ],
    cmdclass={
        "verify": VerifyVersionCommand,
    },
)
