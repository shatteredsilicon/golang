#!/bin/sh

set -ex

if [ $(hash dpkg 2>/dev/null; echo $?) -eq 0 ]; then
    DETECT_DIST=deb
elif [ $(hash rpm 2>/dev/null; echo $?) -eq 0 ]; then
    DETECT_DIST=rpm
else
    DETECT_DIST=unknown
fi

GO_VERSION=${GO_VERSION:-1.24.2}
PACK_DIST=${PACK_DIST:-$DETECT_DIST}

# prepare
GO_VERSION=${GO_VERSION} PACK_DIST=${PACK_DIST} ./prep.sh

# make
GO_VERSION=${GO_VERSION} PACK_DIST=${PACK_DIST} ./make.sh