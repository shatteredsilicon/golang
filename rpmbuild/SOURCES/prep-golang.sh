#!/bin/bash

set -e

GO_VERSION="1.20.12"
PKG_RELEASE="1"

rm -f *.tar.gz

wget https://github.com/golang/go/archive/refs/tags/go${GO_VERSION}.tar.gz

wget https://github.com/golang-fips/go/archive/refs/tags/go${GO_VERSION}-${PKG_RELEASE}-openssl-fips.tar.gz
