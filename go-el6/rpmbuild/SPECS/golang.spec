# Dedicated EL6/x86_64 packaging for Go <= 1.23.x.
# Keep this spec independent from the EL7+ packaging in ../../rpmbuild.

# Go build IDs/debug extraction are intentionally disabled for the toolchain.
%global debug_package %{nil}

# The source/tests packages contain binary-like test data.
%global _binaries_in_noarch_packages_terminate_build 0

# Do not strip Go archives and DWARF test data.
%global __strip /bin/true

# RHEL/CentOS 6 automatically runs brp-python-bytecompile over every .py file
# in the buildroot. That would create Python-2-specific runtime-gdb.pyc and
# runtime-gdb.pyo files under GOROOT after our package file lists have already
# been generated.
#
# runtime-gdb.py is a GDB helper shipped as source by Go and must not be
# byte-compiled as part of the Go source package. Preserve the other relevant
# EL6 build-root policies while intentionally omitting brp-python-bytecompile.
%global __os_install_post \
    /usr/lib/rpm/brp-compress \
    %{!?__debug_package:/usr/lib/rpm/brp-strip %{__strip}} \
    /usr/lib/rpm/brp-strip-static-archive %{__strip} \
    /usr/lib/rpm/brp-strip-comment-note %{__strip} %{__objdump} \
%{nil}

# Avoid generated libc dependencies for the Go source/test payloads. Runtime
# dependencies are declared explicitly below.
%define _use_internal_dependency_generator 0
%define __find_requires %{nil}

%global goroot %{_prefix}/lib/%{name}
%global gopath %{_datadir}/gocode
%global gohostarch amd64

%global toolset_root /opt/rh/devtoolset-7/root/usr
%global toolset_cc %{toolset_root}/bin/gcc
%global toolset_cxx %{toolset_root}/bin/g++

%{!?upstream_version: %global upstream_version 1.23.12}
%{!?bootstrap_version: %global bootstrap_version 1.20.14}

Name:           golang
Version:        %{upstream_version}
Release:        1%{?dist}
Summary:        The Go Programming Language
Group:          Development/Languages
License:        BSD and Public Domain
URL:            https://go.dev

Source0:        go%{upstream_version}.src.tar.gz
# Allow the runtime traceback default to be overridden with rpm_crashtraceback.
Source1:        fedora.go
# Go 1.22 and Go 1.23 require a Go 1.20 bootstrap compiler.
Source2:        go%{bootstrap_version}.linux-amd64.tar.gz
Source100:      golang-gdbinit

Patch1:         0001-Modify-go.env.patch
Patch2:         0002-EL6-link-race-runtime-with-librt.patch

BuildRequires:  bash
BuildRequires:  devtoolset-7-binutils
BuildRequires:  devtoolset-7-gcc
BuildRequires:  devtoolset-7-gcc-c++
BuildRequires:  findutils
BuildRequires:  glibc-devel
BuildRequires:  glibc-static
BuildRequires:  grep
BuildRequires:  gzip
BuildRequires:  make
BuildRequires:  net-tools
BuildRequires:  patch
# EL6 equivalent of Fedora's modern pcre2-devel test dependency.
BuildRequires:  pcre-devel
BuildRequires:  perl
BuildRequires:  pkgconfig
BuildRequires:  procps
BuildRequires:  redhat-rpm-config
BuildRequires:  sed
BuildRequires:  which
BuildRequires:  tar

Provides:       go = %{version}-%{release}
Requires:       %{name}-bin = %{version}-%{release}
Requires:       %{name}-src = %{version}-%{release}

ExclusiveArch:  x86_64

%description
Go is an open source programming language that makes it easy to build simple,
reliable, and efficient software.

This package is built specifically for EL6 x86_64. Go 1.23.12 is the final Go
release line that supports the Linux 2.6.32 kernel used by stock RHEL/CentOS 6.

%package docs
Summary:        Go compiler documentation
Group:          Documentation
Requires:       %{name} = %{version}-%{release}
BuildArch:      noarch

%description docs
Documentation for the Go compiler and standard library.

%package misc
Summary:        Go compiler miscellaneous sources
Group:          Development/Languages
Requires:       %{name} = %{version}-%{release}
BuildArch:      noarch

%description misc
Miscellaneous source files shipped with the Go toolchain.

%package tests
Summary:        Go compiler tests for the standard library
Group:          Development/Languages
Requires:       %{name} = %{version}-%{release}
BuildArch:      noarch

%description tests
Tests and test data shipped with the Go toolchain.

%package src
Summary:        Go compiler source tree
Group:          Development/Languages
BuildArch:      noarch

%description src
The Go compiler and standard library source tree.

%package bin
Summary:        Go compiler and core tools
Group:          Development/Languages
Provides:       %{name}-go = %{version}-%{release}
Requires:       %{name} = %{version}-%{release}
Requires:       glibc
Requires:       git
Requires:       devtoolset-7-binutils
Requires:       devtoolset-7-gcc
Requires:       devtoolset-7-gcc-c++

%description bin
The Go compiler, linker, formatter, and supporting tools.

%prep
%setup -q -n go
%patch1 -p1
%patch2 -p1

cp -p %{SOURCE1} ./src/runtime/

rm -rf %{_builddir}/go-bootstrap
mkdir -p %{_builddir}/go-bootstrap
tar -xzf %{SOURCE2} -C %{_builddir}/go-bootstrap

test -x %{_builddir}/go-bootstrap/go/bin/go
%{_builddir}/go-bootstrap/go/bin/go version

%build
# devtoolset-7 is required because the system GCC 4.4 in EL6 is too old for
# supported cgo builds. Source the SCL environment for its runtime libraries,
# but record absolute compiler paths in the Go toolchain for installed use.
. /opt/rh/devtoolset-7/enable

export GOROOT_BOOTSTRAP=%{_builddir}/go-bootstrap/go
export GOROOT_FINAL=%{goroot}

export GOHOSTOS=linux
export GOHOSTARCH=%{gohostarch}
export GOOS=linux
export GOARCH=%{gohostarch}
export GOAMD64=v1
export CGO_ENABLED=1
export GOTOOLCHAIN=local

export CC=%{toolset_cc}
export CXX=%{toolset_cxx}
export CC_FOR_TARGET=%{toolset_cc}
export CXX_FOR_TARGET=%{toolset_cxx}

export CFLAGS="$RPM_OPT_FLAGS"
export LDFLAGS="$RPM_LD_FLAGS"

cd src
./make.bash -v
cd ..

%install
rm -rf $RPM_BUILD_ROOT

# Remove the transient Go build cache before packaging.
rm -rf pkg/obj/go-build/*

mkdir -p $RPM_BUILD_ROOT%{_bindir}
mkdir -p $RPM_BUILD_ROOT%{goroot}

cp -apv api bin doc lib pkg src misc test go.env VERSION \
    $RPM_BUILD_ROOT%{goroot}

# Keep source/archive timestamps stable so the installed Go toolchain does not
# decide that its standard library needs to be rebuilt.
find $RPM_BUILD_ROOT%{goroot}/src \
    -exec touch -r $RPM_BUILD_ROOT%{goroot}/VERSION "{}" \;
touch $RPM_BUILD_ROOT%{goroot}/pkg
find $RPM_BUILD_ROOT%{goroot}/pkg \
    -exec touch -r $RPM_BUILD_ROOT%{goroot}/pkg "{}" \;

cwd=$(pwd)
src_list=$cwd/go-src.list
pkg_list=$cwd/go-pkg.list
misc_list=$cwd/go-misc.list
docs_list=$cwd/go-docs.list
tests_list=$cwd/go-tests.list

rm -f "$src_list" "$pkg_list" "$misc_list" "$docs_list" "$tests_list"
touch "$src_list" "$pkg_list" "$misc_list" "$docs_list" "$tests_list"

pushd $RPM_BUILD_ROOT%{goroot}
    find src/ -type d \
        -a \( ! -name testdata -a ! -ipath '*/testdata/*' \) \
        -printf '%%%dir %{goroot}/%p\n' >> "$src_list"
    find src/ ! -type d \
        -a \( ! -ipath '*/testdata/*' -a ! -name '*_test.go' \) \
        -printf '%{goroot}/%p\n' >> "$src_list"

    find bin/ pkg/ -type d \
        -printf '%%%dir %{goroot}/%p\n' >> "$pkg_list"
    find bin/ pkg/ ! -type d \
        -printf '%{goroot}/%p\n' >> "$pkg_list"

    find doc/ -type d \
        -printf '%%%dir %{goroot}/%p\n' >> "$docs_list"
    find doc/ ! -type d \
        -printf '%{goroot}/%p\n' >> "$docs_list"

    find misc/ -type d \
        -printf '%%%dir %{goroot}/%p\n' >> "$misc_list"
    find misc/ ! -type d \
        -printf '%{goroot}/%p\n' >> "$misc_list"

    find test/ -type d \
        -printf '%%%dir %{goroot}/%p\n' >> "$tests_list"
    find test/ ! -type d \
        -printf '%{goroot}/%p\n' >> "$tests_list"
    find src/ -type d \
        -a \( -name testdata -o -ipath '*/testdata/*' \) \
        -printf '%%%dir %{goroot}/%p\n' >> "$tests_list"
    find src/ ! -type d \
        -a \( -ipath '*/testdata/*' -o -name '*_test.go' \) \
        -printf '%{goroot}/%p\n' >> "$tests_list"
    find lib/ -type d \
        -printf '%%%dir %{goroot}/%p\n' >> "$tests_list"
    find lib/ ! -type d \
        -printf '%{goroot}/%p\n' >> "$tests_list"
popd

rm -rf $RPM_BUILD_ROOT%{goroot}/doc/Makefile

# Keep the Fedora-compatible architecture-specific aliases inside GOROOT.
mkdir -p $RPM_BUILD_ROOT%{goroot}/bin/linux_%{gohostarch}
ln -sf %{goroot}/bin/go \
    $RPM_BUILD_ROOT%{goroot}/bin/linux_%{gohostarch}/go
ln -sf %{goroot}/bin/gofmt \
    $RPM_BUILD_ROOT%{goroot}/bin/linux_%{gohostarch}/gofmt

# This EL6 package is isolated from the newer distro packages, so direct
# symlinks are more reliable than depending on distro-specific alternatives.
ln -sf %{goroot}/bin/go $RPM_BUILD_ROOT%{_bindir}/go
ln -sf %{goroot}/bin/gofmt $RPM_BUILD_ROOT%{_bindir}/gofmt

# Own the GOPATH skeleton directly; EL6 does not provide the modern
# go-filesystem package expected by the Fedora spec.
mkdir -p $RPM_BUILD_ROOT%{gopath}/src/github.com
mkdir -p $RPM_BUILD_ROOT%{gopath}/src/bitbucket.org
mkdir -p $RPM_BUILD_ROOT%{gopath}/src/code.google.com/p
mkdir -p $RPM_BUILD_ROOT%{gopath}/src/golang.org/x

mkdir -p $RPM_BUILD_ROOT%{_sysconfdir}/gdbinit.d
cp -p %{SOURCE100} $RPM_BUILD_ROOT%{_sysconfdir}/gdbinit.d/golang.gdb

%check
. /opt/rh/devtoolset-7/enable

export GOROOT=$(pwd -P)
export PATH="$GOROOT/bin:%{toolset_root}/bin:$PATH"
export GOOS=linux
export GOARCH=%{gohostarch}
export GOAMD64=v1
export CGO_ENABLED=1
export GOTOOLCHAIN=local

export CC=%{toolset_cc}
export CXX=%{toolset_cxx}
export CFLAGS="$RPM_OPT_FLAGS"
export LDFLAGS="$RPM_LD_FLAGS"
export GO_TEST_TIMEOUT_SCALE=3

cd src
./run.bash --no-rebuild -v -v -v -k
cd ..

# Drop the build-time compiler overrides before checking the defaults embedded
# in the newly built Go toolchain.
unset CC CXX CC_FOR_TARGET CXX_FOR_TARGET
unset GOOS GOARCH GOAMD64 CGO_ENABLED GOTOOLCHAIN

test "$(go env GOOS)" = "linux"
test "$(go env GOARCH)" = "amd64"
test "$(go env GOAMD64)" = "v1"
test "$(go env CGO_ENABLED)" = "1"
test "$(go env CC)" = "%{toolset_cc}"
test "$(go env CXX)" = "%{toolset_cxx}"
test "$(go env GOTOOLCHAIN)" = "local"

# Explicit cgo smoke test using the compiler recorded in the final toolchain.
rm -rf .rpm-cgo-check
mkdir .rpm-cgo-check
cat > .rpm-cgo-check/main.go <<'EOF2'
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

(
    cd .rpm-cgo-check
    GO111MODULE=off go build -o hello main.go
    ./hello | grep -q '^cgo 42$'
)

%files
%doc LICENSE PATENTS
%doc %{goroot}/VERSION
%dir %{goroot}
%dir %{goroot}/doc
%{goroot}/api/
%{goroot}/lib/time/

%dir %{gopath}
%dir %{gopath}/src
%dir %{gopath}/src/github.com/
%dir %{gopath}/src/bitbucket.org/
%dir %{gopath}/src/code.google.com/
%dir %{gopath}/src/code.google.com/p/
%dir %{gopath}/src/golang.org
%dir %{gopath}/src/golang.org/x

%{_sysconfdir}/gdbinit.d

%files src -f go-src.list

%files docs -f go-docs.list

%files misc -f go-misc.list

%files tests -f go-tests.list

%files bin -f go-pkg.list
%{_bindir}/go
%{_bindir}/gofmt
%{goroot}/bin/linux_%{gohostarch}/go
%{goroot}/bin/linux_%{gohostarch}/gofmt
%{goroot}/go.env

%changelog
* Sun Sep 13 2026 Thien Nguyen <nthien86@gmail.com> - 1.23.12-1
- Add dedicated EL6 x86_64 packaging using a Go 1.20 bootstrap toolchain.
