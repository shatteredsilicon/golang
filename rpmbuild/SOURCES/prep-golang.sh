#!/bin/bash

set -e

GO_VERSION="1.18.9"
PKG_RELEASE="1"

rm -f *.tar.gz

wget https://github.com/golang-fips/go/archive/refs/tags/go${GO_VERSION}-${PKG_RELEASE}-openssl-fips.tar.gz
