import setuptools
from setuptools import setup

setup(
    name='pyOnvista',
    version='0.46a',
    url="https://github.com/cloasdata/pyOnvista",
    license='MIT',
    license_files = ('LICENSE',),
    author='Simon Bauer',
    author_email='code@seimenadventure.de',
    description='A tiny API for onvista.de financial website.',
    packages=['pyOnvista'],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent"
    ],
    install_requires = [
            "requests~=2.26.0",
            'lxml~=4.6.4',
    ],
    package_data={'pyOnvista': ['markets.json']}
)