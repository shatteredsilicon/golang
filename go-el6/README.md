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

## Prepare sources

From the repository root:

```bash
cd rpmbuild/SOURCES
./prep-golang-el6.sh 1.23.12
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
mkdir -p rpmbuild/{BUILD,RPMS,SOURCES,SPECS,SRPMS}

cd rpmbuild/SPECS

rpmbuild -bs \
    --define "_topdir $(cd .. && pwd)" \
    --define "dist .el6" \
    golang.spec

mock -r centos-6-x86_64 --rebuild ../SRPMS/golang-1.23.12-1.el6.src.rpm
```

Expected binary packages include at least:

```text
golang-1.23.12-1.el6.x86_64.rpm
golang-bin-1.23.12-1.el6.x86_64.rpm
golang-src-1.23.12-1.el6.noarch.rpm
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