#!/bin/bash -xe

INPUT_PATH=$1
VERSION=$2
OUTPUT_PATH=${3:-.}
PACKAGE_VERSION=${4:-$VERSION}

PACKAGE_NAME=indy-plenum

# copy the sources to a temporary folder
TMP_DIR=$(mktemp -d)
cp -r ${INPUT_PATH}/. ${TMP_DIR}

# prepare the sources
<<<<<<< HEAD:build-scripts/ubuntu-2004/build-plenum.sh
cd ${TMP_DIR}/build-scripts/ubuntu-2004
=======
cd ${TMP_DIR}/build-scripts/ubuntu-1604
>>>>>>> 3cbbc6d1 (added build_python_packages and publishing to PyPI to CD workflow):build-scripts/ubuntu-1604/build-indy-plenum.sh
./prepare-package.sh ${TMP_DIR} plenum ${VERSION} debian-packages

sed -i 's/{package_name}/'${PACKAGE_NAME}'/' "postinst"
sed -i 's/{package_name}/'${PACKAGE_NAME}'/' "prerm"

fpm --input-type "python" \
    --output-type "deb" \
    --architecture "amd64" \
    --depends "python3-pyzmq (= 22.3.0)" \
    --depends "rocksdb (=5.8.8)"\
    --depends "ursa (= 0.3.2-1)"\
    --verbose \
    --python-package-name-prefix "python3"\
    --python-bin "/usr/bin/python3" \
    --exclude "usr/local/lib/python3.8/dist-packages/data" \
    --exclude "usr/local/bin" \
    --exclude "*.pyc" \
    --exclude "*.pyo" \
    --maintainer "Hyperledger <hyperledger-indy@lists.hyperledger.org>" \
    --after-install "postinst" \
    --before-remove "prerm" \
    --name ${PACKAGE_NAME} \
    --version ${PACKAGE_VERSION} \
    --package ${OUTPUT_PATH} \
    ${TMP_DIR}

    # --python-pip "$(which pip)" \
        # ERROR:  download_if_necessary': Unexpected directory layout after easy_install. Maybe file a bug? The directory is /tmp/package-python-build-c42d23109dcca1e98d9f430a04fe79a815f10d8ed7a719633aa969424f94 (RuntimeError)

rm -rf ${TMP_DIR}
