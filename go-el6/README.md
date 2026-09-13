# Go RPM for EL6

This directory contains the EL6-only RPM packaging lane for Go 1.23.x and
older releases. The current spec is intentionally validated against Go 1.23.x;
older release lines belong in this directory but may need version-specific
source/patch adjustments. It is intentionally isolated from the existing `rpmbuild/` tree so that the
EL7-EL10 packaging and Jenkins pipeline do not need to change.

Go 1.23.12 is the last Go release that supports Linux kernel 2.6.32, which is
the stock kernel family used by RHEL/CentOS 6. Go 1.24 and newer are therefore
out of scope for this packaging.

## Design

- Target architecture: `x86_64` only.
- Default Go version: `1.23.12`.
- Default bootstrap toolchain: official `go1.20.14.linux-amd64.tar.gz`.
- C/C++ toolchain: CentOS SCL `devtoolset-7`.
- `GOAMD64=v1` is used to preserve the broadest x86_64 CPU compatibility.
- The RPM is built against the EL6 userspace and EL6 glibc.
- The final RPM must still be runtime-tested on a real EL6 VM with a 2.6.32
  kernel, because Mock shares the build host kernel.

Go 1.22 and 1.23 require a Go 1.20 bootstrap compiler. The fixed 1.20.14
bootstrap is deliberately downloaded as a source artifact and embedded in the
SRPM so that Mock rebuilds are self-contained.

## Fedora patch selection

Only the `0001-Modify-go.env.patch` behavior is needed from the Fedora Go 1.23
package, but the EL6 copy is intentionally reduced to the `GOTOOLCHAIN=local`
change. The existing EL7-EL10 packaging already chose to keep the upstream
`GOPROXY` and `GOSUMDB` defaults, so the EL6 package preserves that repository
policy instead of reintroducing Fedora's older proxy/checksum changes.

- `0005-Skip-TestCrashDumpsAllThreads.patch`: not needed because this EL6 package
  is `x86_64` only; the patch only changes `linux/s390x` behavior.
- `0006-Default-to-ld.bfd-on-ARM64.patch`: not needed because it only affects
  `aarch64`.

The newer top-level packaging patches `fix_cgo_panic-with-gcc15-in-368.patch`
and `skip_lsan_tests.patch` are also intentionally not used here. They address
newer compiler/architecture issues that are unrelated to this EL6 x86_64
build.

`fedora.go` and `golang-gdbinit` are copied into this directory rather than
symlinked to the existing `rpmbuild/SOURCES` tree. Source files referenced by a
spec must be physically present in the SRPM; keeping this tree self-contained
also makes the resulting SRPM reproducible outside the original Git checkout.

## Prepare sources

From the repository root:

```bash
cd go-el6/rpmbuild/SOURCES
./prep-golang-el6.sh 1.23.12
cd ../../..
```

The preparation script downloads both the requested Go source tarball and the
Go bootstrap binary tarball. It obtains SHA-256 values from the official Go
download metadata and verifies both archives before keeping them.

`prep-golang-el6.sh` is intentionally a separate helper rather than a symlink to
the existing `rpmbuild/SOURCES/prep-golang.sh`: the existing helper downloads
only the target source archive, while an EL6 build also needs the bootstrap Go
archive.

For an older Go release, pass the version explicitly. The bootstrap version may
also be overridden when an older release requires a different bootstrap:

```bash
BOOTSTRAP_VERSION=1.20.14 \
  go-el6/rpmbuild/SOURCES/prep-golang-el6.sh 1.23.12
```

## Build with Mock

The examples below assume the custom EL6 Mock target is installed as
`centos-6-x86_64` and contains the CentOS 6.10 base/updates/extras plus SCLo
repositories required for `devtoolset-7`.

```bash
GO_VERSION=1.23.12
BOOTSTRAP_VERSION=1.20.14

rm -rf go-el6/result-srpm go-el6/result-rpm
mkdir -p go-el6/result-srpm go-el6/result-rpm

mock -r centos-6-x86_64 \
  --buildsrpm \
  --spec go-el6/rpmbuild/SPECS/golang.spec \
  --sources go-el6/rpmbuild/SOURCES \
  --define "upstream_version ${GO_VERSION}" \
  --define "bootstrap_version ${BOOTSTRAP_VERSION}" \
  --resultdir go-el6/result-srpm

#
# Select only the SRPM produced for this EL6 build.
#
# Do not use a generic "*.src.rpm" match here.  An older/stale SRPM without
# the .el6 dist tag (for example golang-1.23.12-1.src.rpm) may otherwise be
# selected and then rebuilt with Release=1.el6.  Mock would consequently see
# both the original and rebuilt SRPM in /builddir/build/SRPMS and fail with:
#
#   Expected to find single rebuilt srpm, found 2
#
SRPMS=$(find go-el6/result-srpm -maxdepth 1 -type f \
  -name "golang-${GO_VERSION}-*.el6.src.rpm" -print)

SRPM_COUNT=$(printf '%s\n' "$SRPMS" | sed '/^$/d' | wc -l)

if [ "$SRPM_COUNT" -ne 1 ]; then
  echo "ERROR: expected exactly one EL6 SRPM, found ${SRPM_COUNT}:" >&2
  printf '%s\n' "$SRPMS" >&2
  exit 1
fi

SRPM="$SRPMS"
 
mock -r centos-6-x86_64 --clean

mock -r centos-6-x86_64 \
  --rebuild "$SRPM" \
  --resultdir go-el6/result-rpm
```

Expected binary packages include at least:

```text
golang-1.23.12-1.el6.x86_64.rpm
golang-bin-1.23.12-1.el6.x86_64.rpm
golang-src-1.23.12-1.el6.noarch.rpm
```

## Validate the Mock result

```bash
rpm -qpi go-el6/result-rpm/golang-1.23.12-1.el6.x86_64.rpm
rpm -qpi go-el6/result-rpm/golang-bin-1.23.12-1.el6.x86_64.rpm
```

Install the complete package set into a fresh Mock chroot and verify the
compiler defaults:

```bash
mock -r centos-6-x86_64 --clean
mock -r centos-6-x86_64 --init
BINARY_RPMS=$(find go-el6/result-rpm -maxdepth 1 -type f \
  -name 'golang-*.rpm' ! -name '*.src.rpm' -print)
test -n "$BINARY_RPMS"
mock -r centos-6-x86_64 --install $BINARY_RPMS

mock -r centos-6-x86_64 --chroot -- go version
mock -r centos-6-x86_64 --chroot -- go env GOOS GOARCH GOAMD64 CGO_ENABLED CC CXX GOTOOLCHAIN
```

The important values are:

```text
GOOS=linux
GOARCH=amd64
GOAMD64=v1
CGO_ENABLED=1
CC=/opt/rh/devtoolset-7/root/usr/bin/gcc
CXX=/opt/rh/devtoolset-7/root/usr/bin/g++
GOTOOLCHAIN=local
```

## Final EL6 runtime validation

Mock is a chroot and uses the build host kernel. Before publishing the RPM,
install it on a real RHEL/CentOS 6 x86_64 VM and verify that `uname -r` reports
the expected 2.6.32 kernel family.

Then run:

```bash
go version

go env GOOS GOARCH GOAMD64 CGO_ENABLED CC CXX GOTOOLCHAIN

cat >/tmp/hello.go <<'EOF2'
package main

import "fmt"

func main() {
    fmt.Println("Go on EL6 works")
}
EOF2

cd /tmp
go build -o hello hello.go
./hello
```

Also validate cgo on the real EL6 VM:

```bash
cat >/tmp/hello-cgo.go <<'EOF2'
package main

/*
#include <stdlib.h>
*/
import "C"

import "fmt"

func main() {
    fmt.Println("cgo", C.int(42))
}
EOF2

cd /tmp
CGO_ENABLED=1 go build -o hello-cgo hello-cgo.go
./hello-cgo
```