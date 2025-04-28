#!/bin/sh

set -ex

GO_VERSION=${GO_VERSION:-unknown}
PACK_DIST=${PACK_DIST:-unknown}

if [ $PACK_DIST = 'deb' ]; then
    cd "golang-${GO_VERSION}";
        DEBIAN_GO_VERSION=${GO_VERSION} dpkg-buildpackage -T gencontrol \
        && DEBIAN_GO_VERSION=${GO_VERSION} dpkg-buildpackage -F -us -uc
elif [ $PACK_DIST = 'rpm' ]; then
    cd rpmbuild;
        rpmbuild -ba --define "_topdir `pwd`" SPECS/golang.spec
else
    echo >&2 "error: unsupported dist: $PACK_DIST"; exit 1
fi