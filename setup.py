#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
"""The setup.py file."""

import os
import sys

from setuptools import find_packages, setup
from setuptools.command.install import install

VERSION = "0.3.15"

URL = "https://github.com/zxdavb/evohome-async"

with open("README.md", "r") as fh:
    LONG_DESCRIPTION = fh.read()


class VerifyVersionCommand(install):
    """Custom command to verify that the git tag matches our VERSION."""

    def run(self):
        tag = os.getenv("CIRCLE_TAG")
        if tag != VERSION:
            info = f"The git tag: '{tag}' does not match the package ver: '{VERSION}'"
            sys.exit(info)


setup(
    name="evohome-async",
    description="An async client for connecting to Honeywell's TCC RESTful API.",
    keywords=["evohome", "total connect comfort", "round thermostat"],
    author="Andrew Stock & David Bonnes",
    author_email="zxdavb@gmail.com",
    url=URL,
    download_url=f"{URL}/archive/{VERSION}.tar.gz",
    install_requires=[val.strip() for val in open("requirements.txt")],
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
