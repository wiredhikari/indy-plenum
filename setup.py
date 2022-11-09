import os
import sys
import subprocess

import distutils.cmd
from setuptools import setup, find_packages
from setuptools.command.install import install
from setuptools.command.develop import develop

v = sys.version_info
if sys.version_info < (3, 8):
    msg = "FAIL: Requires Python 3.8 or later, " \
          "but setup.py was run using {}.{}.{}"
    v = sys.version_info
    print(msg.format(v.major, v.minor, v.micro))
    # noinspection PyPackageRequirements
    print("NOTE: Installation failed. Run setup.py using python3")
    sys.exit(1)

try:
    here = os.path.abspath(os.path.dirname(__file__))
except NameError:
    # it can be the case when we are being run as script or frozen
    here = os.path.abspath(os.path.dirname(sys.argv[0]))

metadata = {'__file__': os.path.join(here, 'plenum', '__metadata__.py')}
with open(metadata['__file__'], 'r') as f:
    exec(f.read(), metadata)

<<<<<<< HEAD
<<<<<<< HEAD
<<<<<<< HEAD
<<<<<<< HEAD
tests_require = ['attrs==19.1.0', 'pytest==3.3.1', 'pytest-xdist==1.22.1', 'pytest-forked==0.2',
                 'python3-indy==1.16.0-dev-1636', 'pytest-asyncio==0.8.0']
=======
tests_require = ['attrs', 'pytest', 'pytest-xdist', 'pytest-forked',
                 'python3-indy==1.13.0-dev-1420', 'pytest-asyncio']
>>>>>>> 4ac74853 (upgraded rlp library and moved over some deprecated functionality)
=======
tests_require = ['attrs>=20.3.0', 'pytest>=6.2.2', 'pytest-xdist>=2.2.1', 'pytest-forked>=1.3.0',
                 'python3-indy==1.13.0-dev-1420', 'pytest-asyncio>=0.14.0']
>>>>>>> e26dcdb9 (updates setup.py with newer python package versions)
=======
=======
>>>>>>> 5339e856 (bump indy-sdk to v. 1.16.0)
tests_require = ['attrs==20.3.0', 'pytest==6.2.2', 'pytest-xdist==2.2.1', 'pytest-forked==1.3.0',
<<<<<<< HEAD
                 'python3-indy==1.15.0-dev-1625', 'pytest-asyncio==0.14.0']
>>>>>>> 6730d4c4 (publishing of the artifacts for Ubuntu 20.04)
=======
                 'python3-indy==1.16.0.post236', 'pytest-asyncio==0.14.0']
<<<<<<< HEAD
>>>>>>> 43161511 (fix: fix python3-indy requirement)
=======
=======
tests_require = ['attrs==19.1.0', 'pytest==3.3.1', 'pytest-xdist==1.22.1', 'pytest-forked==0.2',
<<<<<<< HEAD
                 'python3-indy==1.16.0', 'pytest-asyncio==0.8.0']
>>>>>>> d9678de0 (bump indy-sdk to v. 1.16.0)
<<<<<<< HEAD
>>>>>>> 5339e856 (bump indy-sdk to v. 1.16.0)
=======
=======
                 'python3-indy==1.16.0-dev-1636', 'pytest-asyncio==0.8.0']
>>>>>>> 1794e72f (Bump indy-sdk to 1.16.0-dev-1636 for the tests.)
>>>>>>> b1bcaff2 (Bump indy-sdk to 1.16.0-dev-1636 for the tests.)


class PyZMQCommand(distutils.cmd.Command):
    description = 'pyzmq install target'

    version = 'pyzmq==22.3.0'
    options = '--install-option=--zmq=bundled'

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        command = ['pip', 'install', self.version, self.options]
        subprocess.check_call(command)


class InstallCommand(install):
    description = 'install target'

    def run(self):
        install.run_command(self, command='pyzmq')
        install.run(self)


class DevelopCommand(develop):
    description = 'develop target'

    def run(self):
        develop.run_command(self, command='pyzmq')
        develop.run(self)


setup(
    cmdclass={
        'install': InstallCommand,
        'develop': DevelopCommand,
        'pyzmq': PyZMQCommand,
    },
    name=metadata['__title__'],
    version=metadata['__version__'],
    author=metadata['__author__'],
    author_email=metadata['__author_email__'],
    maintainer=metadata['__maintainer__'],
    maintainer_email=metadata['__maintainer_email__'],
    url=metadata['__url__'],
    description=metadata['__description__'],
    long_description=metadata['__long_description__'],
    download_url=metadata['__download_url__'],
    license=metadata['__license__'],
    classifiers=[
        "Programming Language :: Python :: 3"
    ],

    keywords='Byzantine Fault Tolerant Plenum',
    packages=find_packages(exclude=['test', 'test.*', 'docs', 'docs*', 'simulation']) + [
        'data', ],
    # TODO move that to MANIFEST.in
    package_data={
        '': ['*.txt', '*.md', '*.rst', '*.json', '*.conf', '*.html',
             '*.css', '*.ico', '*.png', 'LICENSE', 'LEGAL', 'plenum']},
    include_package_data=True,

    install_requires=[
<<<<<<< HEAD
<<<<<<< HEAD
<<<<<<< HEAD
<<<<<<< HEAD
<<<<<<< HEAD
                        'jsonpickle==0.9.6',
                        'ujson==1.33',
                        'prompt_toolkit==0.57',
                        'pygments==2.7.4',
                        'rlp==0.5.1',
                        'sha3==0.2.1',
                        'leveldb',
                        'ioflo==1.5.4',
                        'semver==2.7.9',
                        'base58==1.0.0',
                        'orderedset==2.0.3',
                        'sortedcontainers==1.5.7',
                        'psutil==5.6.6',
                        'importlib-metadata==2.1.3',
                        'portalocker==0.5.7',
                        'libnacl==1.6.1',
                        'six==1.11.0',
                        'intervaltree==2.1.0',
                        'msgpack-python==0.4.6',
                        'python-rocksdb==0.6.9',
                        'python-dateutil==2.6.1',
                        'pympler==0.8',
                        'packaging==19.0',
=======
                        'jsonpickle',
                        'ujson',
                        'prompt_toolkit',
                        'pygments',
                        'rlp',
                        'sha3',
                        'ioflo',
                        'semver',
                        'base58',
                        'orderedset',
                        'sortedcontainers',
                        'psutil',
                        'pip<10.0.0',
                        'portalocker',
                        'libnacl',
                        'six',
                        'intervaltree',
                        'msgpack-python',
                        'python-rocksdb',
                        'python-dateutil',
                        'pympler',
                        'packaging',
>>>>>>> 4ac74853 (upgraded rlp library and moved over some deprecated functionality)
=======
                        'jsonpickle>=2.0.0',
=======
                        'jsonpickle',
>>>>>>> 90060c48 (Remove some pinned dependencies)
                        'ujson>=1.33',
                        'prompt_toolkit>=3.0.16',
                        'pygments>=2.2.0',
                        'rlp<=0.6.0',
                        'sha3',
                        'leveldb>=0.201',
                        'ioflo',
                        'semver',
=======
=======
>>>>>>> a6f53227 (pinned dependencies because of missing support for python 3.5)
                        # 'base58==2.1.0',
>>>>>>> 6730d4c4 (publishing of the artifacts for Ubuntu 20.04)
                        'base58',
                        # pinned because issue with fpm from v4.0.0
                        'importlib_metadata==3.10.1',
                        # 'ioflo==2.0.2',
                        'ioflo',
                        # 'jsonpickle==2.0.0',
                        'jsonpickle',
                        # 'leveldb==0.201',
=======
                        'jsonpickle==0.9.6',
                        'ujson==1.33',
                        'prompt_toolkit==0.57',
                        'pygments==2.7.4',
                        'rlp==0.5.1',
                        'sha3==0.2.1',
>>>>>>> 5bef3129 (pinned dependencies because of missing support for python 3.5)
                        'leveldb',
<<<<<<< HEAD
                        # Pinned because of changing size of `crypto_sign_SECRETKEYBYTES` from 32 to 64
=======
                        'ioflo==1.5.4',
                        'semver==2.7.9',
                        'base58==1.0.0',
                        'orderedset==2.0.3',
                        'sortedcontainers==1.5.7',
                        'psutil==5.6.6',
                        'importlib-metadata==2.1.3',
                        'portalocker==0.5.7',
>>>>>>> 4cd59f88 (remove pip imports in favor of importlib_metadata)
                        'libnacl==1.6.1',
                        # 'msgpack-python==0.5.6',
                        'msgpack-python',
<<<<<<< HEAD
                        'python-rocksdb',
                        'python-dateutil',
                        'pympler>=0.8',
<<<<<<< HEAD
                        'packaging>=20.9',
>>>>>>> e26dcdb9 (updates setup.py with newer python package versions)
=======
                        'packaging',
>>>>>>> 90060c48 (Remove some pinned dependencies)
=======
                        # 'orderedset==2.0.3',
                        'orderedset',
                        # 'packaging==20.9',
                        'packaging',
                        # 'portalocker==2.2.1',
                        'portalocker',
                        'prompt_toolkit>=3.0.18',
                        # 'psutil==5.6.6',
                        'psutil',
                        # Pinned because tests fail with v.0.9
                        'pympler==0.8',
                        # 'python-dateutil==2.8.1',
                        'python-dateutil',
                        # 'python-rocksdb==0.7.0',
                        'python-rocksdb',
>>>>>>> 6730d4c4 (publishing of the artifacts for Ubuntu 20.04)
                        'python-ursa==0.1.1',
                        ### Tests fail without version pin (GHA run: https://github.com/udosson/indy-plenum/actions/runs/1078745445)
                        'rlp==0.6.0',
                        'semver==2.13.0',
                        # 'sha3==0.2.1',
                        'sha3',
                        # 'six==1.15.0',
                        'six',
                        ### Tests fail without version pin (GHA run: https://github.com/udosson/indy-plenum/actions/runs/1078741118)
                        'sortedcontainers==1.5.7',
                        ### Tests fail without version pin (GHA run: https://github.com/udosson/indy-plenum/actions/runs/1078741118)
                        'ujson==1.33',
                        ],

    setup_requires=['pytest-runner==5.3.0'],
    extras_require={
        'tests': tests_require,
        'stats': ['python-firebase'],
        'benchmark': ['pympler==0.8']
    },
    tests_require=tests_require,
    scripts=['scripts/init_plenum_keys',
             'scripts/start_plenum_node',
             'scripts/generate_plenum_pool_transactions',
             'scripts/gen_steward_key', 'scripts/gen_node',
             'scripts/export-gen-txns', 'scripts/get_keys',
             'scripts/udp_sender', 'scripts/udp_receiver', 'scripts/filter_log',
             'scripts/log_stats',
             'scripts/init_bls_keys',
             'scripts/process_logs/process_logs',
             'scripts/process_logs/process_logs.yml']
)
