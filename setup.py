import os
import sys
import subprocess

import distutils.cmd
from setuptools import setup, find_packages
from setuptools.command.install import install
from setuptools.command.develop import develop

v = sys.version_info
if sys.version_info < (3, 5):
    msg = "FAIL: Requires Python 3.5 or later, " \
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


class PyZMQCommand(distutils.cmd.Command):
    description = 'pyzmq install target'

    version = 'pyzmq==18.1.0'
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

    #FIXME -> RTM: a function in rlp is used which is deprecated in newer versions.
    # 'rlp==0.5.1',
    install_requires=[
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
                        'ujson>=1.33',
                        'prompt_toolkit>=3.0.16',
                        'pygments>=2.2.0',
                        'rlp>=0.6.0',
                        'sha3>=0.2.1',
                        'ioflo>=2.0.2',
                        'semver>=2.13.0',
                        'base58>=2.1.0',
                        'orderedset>=2.0.3',
                        'sortedcontainers>=1.5.7',
                        'psutil>=5.6.6',
                        'pip<10.0.0',
                        'portalocker>=2.2.1',
                        'libnacl>=1.7.2',
                        'six>=1.15.0',
                        'intervaltree>=2.1.0',
                        'msgpack-python>=0.5.6',
                        'python-rocksdb>=0.7.0',
                        'python-dateutil>=2.8.1',
                        'pympler>=0.8',
                        'packaging>=20.9',
>>>>>>> e26dcdb9 (updates setup.py with newer python package versions)
                        'python-ursa==0.1.1',
                      ],

    setup_requires=['pytest-runner'],
    extras_require={
        'tests': tests_require,
        'stats': ['python-firebase'],
        'benchmark': ['pympler']
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
