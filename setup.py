import os
import sys

from setuptools import setup
from setuptools.command.install import install

VERSION = "0.3.3b4"

with open("README.md", "r") as fh:
    long_description = fh.read()

class VerifyVersionCommand(install):
    """Custom command to verify that the git tag matches our version"""
    description = 'verify that the git tag matches our version'

    def run(self):
        tag = os.getenv('CIRCLE_TAG')

        if tag != VERSION:
            info = "Git tag: {0} does not match the version of this app: {1}".format(
                tag, VERSION
            )
            sys.exit(info)

setup(
    name='evohome-async',
    version=VERSION,
    description='An async Python client for connecting to the Evohome webservice',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='https://github.com/zxdavb/evohome-async/',
    download_url='https://github.com/zxdavb/evohome-async/tarball/' + VERSION,
    author='Andrew Stock & David Bonnes',
    author_email='zxdavb@bonnes.me',
    license='Apache 2',
    classifiers=[
        'Development Status :: 4 - Beta',
    ],
    keywords=['evohome', 'total connect comfort', 'round thermostat'],
    packages=['evohomeclient', 'evohomeclient2'],
    install_requires=['aiohttp', 'requests'],
    cmdclass={
        'verify': VerifyVersionCommand,
    }
)
