#!/bin/sh

set -ex

GO_VERSION=${GO_VERSION:-unknown}
PACK_DIST=${PACK_DIST:-unknown}

if [ $PACK_DIST = 'deb' ]; then
    rm -rf "golang-${GO_VERSION}"
    mkdir "golang-${GO_VERSION}"
    cp -r debian "golang-${GO_VERSION}"
    cd "golang-${GO_VERSION}";
        wget https://go.dev/dl/go${GO_VERSION}.src.tar.gz -O go${GO_VERSION}.src.tar.gz \
        && wget https://github.com/llvm/llvm-project/archive/$(tar -xOf go${GO_VERSION}.src.tar.gz go/src/runtime/race/README | sed -rn "s/^race_linux_arm64\.syso .* LLVM ([a-z0-9]+).*/\1/p").tar.gz -O llvm.tar.gz
elif [ $PACK_DIST = 'rpm' ]; then
    rpmbuild/SOURCES/prep-golang.sh
else
    echo >&2 "error: unsupported dist: $PACK_DIST"; exit 1
fi