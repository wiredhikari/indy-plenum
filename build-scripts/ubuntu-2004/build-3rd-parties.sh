#!/usr/bin/env bash

set -e
set -x

OUTPUT_PATH=${1:-.}

function build_rocksdb_deb {
    VERSION=$1
    VERSION_TAG="rocksdb-$VERSION"

    git clone https://github.com/evernym/rocksdb.git /tmp/rocksdb
    cd /tmp/rocksdb
    git checkout $VERSION_TAG
    sed -i 's/-m rocksdb@fb.com/-m "Hyperledger <hyperledger-indy@lists.hyperledger.org>"/g' \
        ./build_tools/make_package.sh
    PORTABLE=1 EXTRA_CFLAGS="-fPIC" EXTRA_CXXFLAGS="-fPIC" ./build_tools/make_package.sh $VERSION
    # Install it in the system as it is needed by python-rocksdb.
    make install
    cd -
    cp /tmp/rocksdb/package/rocksdb_${VERSION}_amd64.deb $OUTPUT_PATH
    rm -rf /tmp/rocksdb
}

function build_from_pypi {
    PACKAGE_NAME=$1

    if [ -z $2 ]; then
        PACKAGE_VERSION=""
    else
        PACKAGE_VERSION="==$2"
    fi
    POSTINST_TMP=postinst-${PACKAGE_NAME}
    PREREM_TMP=prerm-${PACKAGE_NAME}
    cp postinst ${POSTINST_TMP}
    cp prerm ${PREREM_TMP}
    if [[ ${PACKAGE_NAME} =~ ^python-* ]]; then
        PACKAGE_NAME_TMP="${PACKAGE_NAME/python-/}"
    else
        PACKAGE_NAME_TMP=$PACKAGE_NAME
    fi
    sed -i 's/{package_name}/python3-'${PACKAGE_NAME_TMP}'/' ${POSTINST_TMP}
    sed -i 's/{package_name}/python3-'${PACKAGE_NAME_TMP}'/' ${PREREM_TMP}

    if [ -z $3 ]; then
        fpm --input-type "python" \
            --output-type "deb" \
            --architecture "amd64" \
            --verbose \
            --python-package-name-prefix "python3"\
            --python-bin "/usr/bin/python3" \
            --exclude "*.pyc" \
            --exclude "*.pyo" \
            --maintainer "Hyperledger <hyperledger-indy@lists.hyperledger.org>" \
            --after-install ${POSTINST_TMP} \
            --before-remove ${PREREM_TMP} \
            --package ${OUTPUT_PATH} \
            ${PACKAGE_NAME}${PACKAGE_VERSION}
    else
        fpm --input-type "python" \
            --output-type "deb" \
            --architecture "amd64" \
            --python-setup-py-arguments "--zmq=bundled" \
            --verbose \
            --python-package-name-prefix "python3"\
            --python-bin "/usr/bin/python3" \
            --exclude "*.pyc" \
            --exclude "*.pyo" \
            --maintainer "Hyperledger <hyperledger-indy@lists.hyperledger.org>" \
            --after-install ${POSTINST_TMP} \
            --before-remove ${PREREM_TMP} \
            --package ${OUTPUT_PATH} \
            ${PACKAGE_NAME}${PACKAGE_VERSION}
            
            # --python-pip "$(which pip)" \
        # ERROR:  download_if_necessary': Unexpected directory layout after easy_install. Maybe file a bug? The directory is /tmp/package-python-build-c42d23109dcca1e98d9f430a04fe79a815f10d8ed7a719633aa969424f94 (RuntimeError)
    fi

    rm ${POSTINST_TMP}
    rm ${PREREM_TMP}
}

# TODO duplicates list from Jenkinsfile.cd
SCRIPT_PATH="${BASH_SOURCE[0]}"
pushd `dirname ${SCRIPT_PATH}` >/dev/null


# Build rocksdb at first
### Can be removed once the code has been updated to run with rocksdb v. 5.17
### Issue 1551: Update RocksDB; https://github.com/hyperledger/indy-plenum/issues/1551
build_rocksdb_deb 5.8.8


#### PyZMQCommand
build_from_pypi pyzmq 18.1.0 bundled


##### install_requires
build_from_pypi base58 
build_from_pypi importlib_metadata
build_from_pypi ioflo 
build_from_pypi jsonpickle 
build_from_pypi leveldb 
build_from_pypi libnacl 1.6.1
build_from_pypi msgpack-python
build_from_pypi orderedset
build_from_pypi packaging 
build_from_pypi portalocker
build_from_pypi prompt-toolkit 3.0.18
build_from_pypi psutil 
build_from_pypi pympler 0.8
build_from_pypi python-dateutil 
build_from_pypi python-rocksdb
build_from_pypi python-ursa 0.1.1
build_from_pypi rlp 0.6.0
build_from_pypi semver 
build_from_pypi sha3 
build_from_pypi six 
build_from_pypi sortedcontainers 1.5.7
build_from_pypi ujson 1.33


