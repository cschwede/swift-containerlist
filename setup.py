# -*- encoding: utf-8 -*-
__author__ = "Christian Schwede <info@cschwede.de>"
name = 'containerlist'
entry_point = '%s.middleware:filter_factory' % (name)
version = '0.3'

from setuptools import setup, find_packages

setup(
    name=name,
    version=version,
    description='Swift guest container middleware',
    license='Apache License (2.0)',
    author='Christian Schwede',
    author_email='info@cschwede.de',
    url='https://github.com/cschwede/swift-%s' % (name),
    packages=find_packages(),
    test_suite='nose.collector',
    classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 2.6',
        'Environment :: No Input/Output (Daemon)'],
    dependency_links = ['http://github.com/openstack/swift/tarball/master#egg=swift-1.9.0'],
    install_requires=['swift'],
    entry_points={
        'paste.filter_factory': ['%s=%s' % (name, entry_point)]
    },
)
