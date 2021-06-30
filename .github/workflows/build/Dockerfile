FROM hyperledger/indy-core-baseci:0.0.3-master
LABEL maintainer="Hyperledger <hyperledger-indy@lists.hyperledger.org>"

<<<<<<< HEAD
<<<<<<< HEAD
RUN apt-key adv --keyserver keyserver.ubuntu.com --recv-keys CE7709D068DB5E88 \
    && apt-get update -y \
    && apt-get install -y \
    python3-nacl \
    libindy-crypto=0.4.5 \
    libindy=1.16.0~1636-xenial \
=======
RUN apt-get update -y && apt-get install -y \
=======
RUN apt-key adv --keyserver keyserver.ubuntu.com --recv-keys CE7709D068DB5E88 \
    && apt-get update -y \
    && apt-get install -y \
>>>>>>> 5d342ce9 (Update CD workflow and package publishing)
    python3-nacl \
    libindy-crypto=0.4.5 \
    libindy=1.15.0~1625 \
>>>>>>> 88b1c363 (Bump libindy ver 1.15.0~1625 for GitHub-Actions)
# rocksdb python wrapper
    libbz2-dev \
    zlib1g-dev \
    liblz4-dev \
    libsnappy-dev \
    rocksdb=5.8.8 \
    ursa=0.3.2-2 \
# Build dependencies
    ruby \
    ruby-dev \
    rubygems \
    gcc \
<<<<<<< HEAD
<<<<<<< HEAD
    make \
# zstd is needed for caching in github actions pipeline
    zstd
=======
    make 
>>>>>>> 88b1c363 (Bump libindy ver 1.15.0~1625 for GitHub-Actions)
=======
    make \
# zstd is needed for caching in github actions pipeline
    zstd
>>>>>>> 48a28ddb (publishing artifacts to jfrog artifactory)

# install fpm
RUN gem install --no-ri --no-rdoc rake fpm

<<<<<<< HEAD
<<<<<<< HEAD
RUN indy_image_clean
=======
RUN indy_image_clean
>>>>>>> 88b1c363 (Bump libindy ver 1.15.0~1625 for GitHub-Actions)
=======
RUN indy_image_clean
>>>>>>> 48a28ddb (publishing artifacts to jfrog artifactory)
