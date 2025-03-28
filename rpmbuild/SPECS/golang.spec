%undefine _missing_build_ids_terminate_build

%global bcond_with strict_fips

# build ids are not currently generated:
# https://code.google.com/p/go/issues/detail?id=5238
#
# also, debuginfo extraction currently fails with
# "Failed to write file: invalid section alignment"
%global debug_package %{nil}

# we are shipping the full contents of src in the data subpackage, which
# contains binary-like things (ELF data for tests, etc)
%global _binaries_in_noarch_packages_terminate_build 0

# Do not check any files in doc or src for requires
%global __requires_exclude_from ^(%{_datadir}|/usr/lib)/%{name}/(doc|src)/.*$

# Don't alter timestamps of especially the .a files (or else go will rebuild later)
# Actually, don't strip at all since we are not even building debug packages and this corrupts the dwarf testdata
%global __strip /bin/true

# rpmbuild magic to keep from having meta dependency on libc.so.6
%define _use_internal_dependency_generator 0
%define __find_requires %{nil}
%global __spec_install_post /usr/lib/rpm/check-rpaths   /usr/lib/rpm/check-buildroot  \
  /usr/lib/rpm/brp-compress

# Define GOROOT macros
%global goroot          %{_prefix}/lib/%{name}
%global gopath          %{_datadir}/gocode
%global golang_arches   x86_64 aarch64 ppc64le s390x
%global golibdir        %{_libdir}/%{name}

# Golang build options.

# Build golang using external/internal(close to cgo disabled) linking.
%ifarch x86_64 ppc64le %{arm} aarch64 s390x
%global external_linker 1
%else
%global external_linker 0
%endif

# Build golang with cgo enabled/disabled(later equals more or less to internal linking).
%ifarch x86_64 ppc64le %{arm} aarch64 s390x
%global cgo_enabled 1
%else
%global cgo_enabled 0
%endif

# Use golang/gcc-go as bootstrap compiler
%ifarch %{golang_arches}
%global golang_bootstrap 1
%else
%global golang_bootstrap 0
%endif

# Controls what ever we fail on failed tests
%ifarch x86_64 %{arm} aarch64 ppc64le s390x
%if 0%{?rhel} == 7
%global fail_on_tests 0
%else
%global fail_on_tests 1
%endif
%endif

# Build golang shared objects for stdlib
%ifarch 0
%global shared 1
%else
%global shared 0
%endif

# Pre build std lib with -race enabled
%ifarch x86_64
%global race 1
%else
%global race 0
%endif

%ifarch x86_64
%global gohostarch  amd64
%endif
%ifarch %{arm}
%global gohostarch  arm
%endif
%ifarch aarch64
%global gohostarch  arm64
%endif
%ifarch ppc64
%global gohostarch  ppc64
%endif
%ifarch ppc64le
%global gohostarch  ppc64le
%endif
%ifarch s390x
%global gohostarch  s390x
%endif

%global go_api 1.18
%global go_version 1.18.9
%global pkg_release 1

Name:           golang
Version:        %{go_version}
Release:        2%{?dist}
Summary:        The Go Programming Language
# source tree includes several copies of Mark.Twain-Tom.Sawyer.txt under Public Domain
License:        BSD and Public Domain
URL:            http://golang.org/
# make possible to override default traceback level at build time by setting build tag rpm_crashtraceback
Source0:        go%{go_version}-%{pkg_release}-openssl-fips.tar.gz

Source1:        fedora.go

# The compiler is written in Go. Needs go(1.4+) compiler for build.
# Actual Go based bootstrap compiler provided by above source.
%if !%{golang_bootstrap}
BuildRequires:  gcc-go >= 5
%else
BuildRequires:  golang
%endif
%if 0%{?rhel} > 6 || 0%{?fedora} > 0
BuildRequires:  hostname
%else
BuildRequires:  net-tools
%endif
# For OpenSSL FIPS
BuildRequires:  openssl-devel
# for tests
BuildRequires:  pcre-devel, glibc-static, perl

Provides:       go = %{version}-%{release}
%if 0%{?rhel} == 7
Provides:       go-srpm-macros
Requires:       go-srpm-macros
%endif
Requires:       %{name}-bin = %{version}-%{release}
Requires:       %{name}-src = %{version}-%{release}
Requires:       openssl-devel
Requires:       diffutils

# we had been just removing the zoneinfo.zip, but that caused tests to fail for users that 
# later run `go test -a std`. This makes it only use the zoneinfo.zip where needed in tests.
Patch215:       go1.5-zoneinfo_testing_only.patch

# Proposed patch by jcajka https://golang.org/cl/86541
Patch221:       fix_TestScript_list_std.patch

# static linking of dlopen is unsupported
Patch226:      disable_static_external_tests.patch

Patch223: remove_ed25519vectors_test.patch

Patch227: cmd-link-use-correct-path-for-dynamic-loader-on-ppc6.patch

Patch228: do-not-reuse-far-trampolines.patch
Patch229: big-endian.patch

# Having documentation separate was broken
Obsoletes:      %{name}-docs < 1.1-4

# RPM can't handle symlink -> dir with subpackages, so merge back
Obsoletes:      %{name}-data < 1.1.1-4

# These are the only RHEL/Fedora architectures that we compile this package for
ExclusiveArch:  %{golang_arches}

Source100:      golang-gdbinit
Source101:      golang-prelink.conf
%if 0%{?rhel} == 7
Source102:      macros.golang
%endif

%description
%{summary}.

%package       docs
Summary:       Golang compiler docs
Requires:      %{name} = %{version}-%{release}
BuildArch:     noarch
Obsoletes:     %{name}-docs < 1.1-4

%description   docs
%{summary}.

%package       misc
Summary:       Golang compiler miscellaneous sources
Requires:      %{name} = %{version}-%{release}
BuildArch:     noarch

%description   misc
%{summary}.

%package       tests
Summary:       Golang compiler tests for stdlib
Requires:      %{name} = %{version}-%{release}
BuildArch:     noarch

%description   tests
%{summary}.

%package        src
Summary:        Golang compiler source tree
BuildArch:      noarch

%description    src
%{summary}

%package        bin
Summary:        Golang core compiler tools
Requires:       %{name} = %{version}-%{release}

# We strip the meta dependency, but go does require glibc.
# This is an odd issue, still looking for a better fix.
Requires:       glibc
Requires:       /usr/bin/gcc
%description    bin
%{summary}

# Workaround old RPM bug of symlink-replaced-with-dir failure
%pretrans -p <lua>
for _,d in pairs({"api", "doc", "include", "lib", "src"}) do
  path = "%{goroot}/" .. d
  if posix.stat(path, "type") == "link" then
    os.remove(path)
    posix.mkdir(path)
  end
end

%if %{shared}
%package        shared
Summary:        Golang shared object libraries

%description    shared
%{summary}.
%endif

%if %{race}
%package        race
Summary:        Golang std library with -race enabled

Requires:       %{name} = %{version}-%{release}

%description    race
%{summary}
%endif

%prep
%setup -q -n go-go%{go_version}-%{pkg_release}-openssl-fips

%patch215 -p1
%patch221 -p1
%patch223 -p1
%patch226 -p1
%patch227 -p1
%patch228 -p1
%patch229 -p1

cp %{SOURCE1} ./src/runtime/

%build
set -xe
# print out system information
uname -a
cat /proc/cpuinfo
cat /proc/meminfo

# bootstrap compiler GOROOT
%if !%{golang_bootstrap}
export GOROOT_BOOTSTRAP=/
%else
export GOROOT_BOOTSTRAP=/opt/rh/go-toolset-1.10/root/usr/lib/go-toolset-1.10-golang
%endif

# set up final install location
export GOROOT_FINAL=%{goroot}

export GOHOSTOS=linux
export GOHOSTARCH=%{gohostarch}

pushd src
# use our gcc options for this build, but store gcc as default for compiler
export CFLAGS="$RPM_OPT_FLAGS"
export LDFLAGS="$RPM_LD_FLAGS"
export CC="gcc"
export CC_FOR_TARGET="gcc"
export GOOS=linux
export GOARCH=%{gohostarch}

DEFAULT_GO_LD_FLAGS=""
%if !%{external_linker}
export GO_LDFLAGS="-linkmode internal $DEFAULT_GO_LD_FLAGS"
%else
# Only pass a select subset of the external hardening flags. We do not pass along
# the default $RPM_LD_FLAGS as on certain arches Go does not fully, correctly support
# building in PIE mode.
export GO_LDFLAGS="\"-extldflags=-Wl,-z,now,-z,relro\" $DEFAULT_GO_LD_FLAGS"
%endif
%if !%{cgo_enabled}
export CGO_ENABLED=0
%endif
./make.bash --no-clean
popd

# build shared std lib
%if %{shared}
GOROOT=$(pwd) PATH=$(pwd)/bin:$PATH go install -buildmode=shared std
%endif

%if %{race}
GOROOT=$(pwd) PATH=$(pwd)/bin:$PATH go install -race std
%endif


%install

rm -rf $RPM_BUILD_ROOT

# create the top level directories
mkdir -p $RPM_BUILD_ROOT%{_bindir}
mkdir -p $RPM_BUILD_ROOT%{goroot}

# remove bootstrap binaries
rm -rf pkg/bootstrap/bin

# install everything into libdir (until symlink problems are fixed)
# https://code.google.com/p/go/issues/detail?id=5830
cp -apv api bin doc lib pkg src misc test VERSION \
   $RPM_BUILD_ROOT%{goroot}

# bz1099206
find $RPM_BUILD_ROOT%{goroot}/src -exec touch -r $RPM_BUILD_ROOT%{goroot}/VERSION "{}" \;
# and level out all the built archives
touch $RPM_BUILD_ROOT%{goroot}/pkg
find $RPM_BUILD_ROOT%{goroot}/pkg -exec touch -r $RPM_BUILD_ROOT%{goroot}/pkg "{}" \;
# generate the spec file ownership of this source tree and packages
cwd=$(pwd)
src_list=$cwd/go-src.list
pkg_list=$cwd/go-pkg.list
shared_list=$cwd/go-shared.list
race_list=$cwd/go-race.list
misc_list=$cwd/go-misc.list
docs_list=$cwd/go-docs.list
tests_list=$cwd/go-tests.list
rm -f $src_list $pkg_list $docs_list $misc_list $tests_list $shared_list $race_list
touch $src_list $pkg_list $docs_list $misc_list $tests_list $shared_list $race_list
pushd $RPM_BUILD_ROOT%{goroot}
    find src/ -type d -a \( ! -name testdata -a ! -ipath '*/testdata/*' \) -printf '%%%dir %{goroot}/%p\n' >> $src_list
    find src/ ! -type d -a \( ! -ipath '*/testdata/*' -a ! -name '*_test*.go' \) -printf '%{goroot}/%p\n' >> $src_list

    find bin/ pkg/ -type d -a ! -path '*_dynlink/*' -a ! -path '*_race/*' -printf '%%%dir %{goroot}/%p\n' >> $pkg_list
    find bin/ pkg/ ! -type d -a ! -path '*_dynlink/*' -a ! -path '*_race/*' -printf '%{goroot}/%p\n' >> $pkg_list

    find doc/ -type d -printf '%%%dir %{goroot}/%p\n' >> $docs_list
    find doc/ ! -type d -printf '%{goroot}/%p\n' >> $docs_list

    find misc/ -type d -printf '%%%dir %{goroot}/%p\n' >> $misc_list
    find misc/ ! -type d -printf '%{goroot}/%p\n' >> $misc_list

%if %{shared}
    mkdir -p %{buildroot}/%{_libdir}/
    mkdir -p %{buildroot}/%{golibdir}/
    for file in $(find .  -iname "*.so" ); do
        chmod 755 $file
        mv  $file %{buildroot}/%{golibdir}
        pushd $(dirname $file)
        ln -fs %{golibdir}/$(basename $file) $(basename $file)
        popd
        echo "%%{goroot}/$file" >> $shared_list
        echo "%%{golibdir}/$(basename $file)" >> $shared_list
    done
    
    find pkg/*_dynlink/ -type d -printf '%%%dir %{goroot}/%p\n' >> $shared_list
    find pkg/*_dynlink/ ! -type d -printf '%{goroot}/%p\n' >> $shared_list
%endif

%if %{race}

    find pkg/*_race/ -type d -printf '%%%dir %{goroot}/%p\n' >> $race_list
    find pkg/*_race/ ! -type d -printf '%{goroot}/%p\n' >> $race_list

%endif

    find test/ -type d -printf '%%%dir %{goroot}/%p\n' >> $tests_list
    find test/ ! -type d -printf '%{goroot}/%p\n' >> $tests_list
    find src/ -type d -a \( -name testdata -o -ipath '*/testdata/*' \) -printf '%%%dir %{goroot}/%p\n' >> $tests_list
    find src/ ! -type d -a \( -ipath '*/testdata/*' -o -name '*_test*.go' \) -printf '%{goroot}/%p\n' >> $tests_list
    # this is only the zoneinfo.zip
    find lib/ -type d -printf '%%%dir %{goroot}/%p\n' >> $tests_list
    find lib/ ! -type d -printf '%{goroot}/%p\n' >> $tests_list
popd

# remove the doc Makefile
rm -rfv $RPM_BUILD_ROOT%{goroot}/doc/Makefile

# put binaries to bindir, linked to the arch we're building,
# leave the arch independent pieces in {goroot}
mkdir -p $RPM_BUILD_ROOT%{goroot}/bin/linux_%{gohostarch}
ln -sf %{goroot}/bin/go $RPM_BUILD_ROOT%{_bindir}/go
ln -sf %{goroot}/bin/gofmt $RPM_BUILD_ROOT%{_bindir}/gofmt

# ensure these exist and are owned
mkdir -p $RPM_BUILD_ROOT%{gopath}/src/github.com
mkdir -p $RPM_BUILD_ROOT%{gopath}/src/bitbucket.org
mkdir -p $RPM_BUILD_ROOT%{gopath}/src/code.google.com/p
mkdir -p $RPM_BUILD_ROOT%{gopath}/src/golang.org/x

# gdbinit
mkdir -p $RPM_BUILD_ROOT%{_sysconfdir}/gdbinit.d
cp -av %{SOURCE100} $RPM_BUILD_ROOT%{_sysconfdir}/gdbinit.d/golang.gdb

# prelink blacklist
mkdir -p $RPM_BUILD_ROOT%{_sysconfdir}/prelink.conf.d
cp -av %{SOURCE101} $RPM_BUILD_ROOT%{_sysconfdir}/prelink.conf.d/golang.conf

%if 0%{?rhel} == 7
# rpm macros
mkdir -p %{buildroot}
mkdir -p $RPM_BUILD_ROOT%{_rpmconfigdir}/macros.d
cp -av %{SOURCE102} $RPM_BUILD_ROOT%{_rpmconfigdir}/macros.d/macros.golang
%endif

# Quick fix for the rhbz#2014704
sed -i 's/const defaultGO_LDSO = `.*`/const defaultGO_LDSO = ``/' $RPM_BUILD_ROOT%{goroot}/src/internal/buildcfg/zbootstrap.go

%check
export GOROOT=$(pwd -P)
export PATH="$GOROOT"/bin:"$PATH"
cd src

# Add some sanity checks.
echo "GO VERSION:"
go version

echo "GO ENVIRONMENT:"
go env

export CC="gcc"
export CFLAGS="$RPM_OPT_FLAGS"
export LDFLAGS="$RPM_LD_FLAGS"
%if !%{external_linker}
export GO_LDFLAGS="-linkmode internal"
%else
export GO_LDFLAGS="-extldflags '$RPM_LD_FLAGS'"
%endif
%if !%{cgo_enabled} || !%{external_linker}
export CGO_ENABLED=0
%endif

# make sure to not timeout
export GO_TEST_TIMEOUT_SCALE=10

export GO_TEST_RUN=""
%ifarch aarch64
  export GO_TEST_RUN="-run=!testshared"
%endif

%if %{fail_on_tests}

# TestEd25519Vectors needs network connectivity but it should be cover by
# this test https://pkgs.devel.redhat.com/cgit/tests/golang/tree/Regression/internal-testsuite/runtest.sh#n127
export DISABLE_Ed25519_TEST="-run=!^TestEd25519Vectors$"

./run.bash --no-rebuild -v -v -v -k $GO_TEST_RUN $DISABLE_Ed25519_TEST

# Run tests with FIPS enabled.
export GOLANG_FIPS=1
pushd crypto
  # Run all crypto tests but skip TLS, we will run FIPS specific TLS tests later
  go test $(go list ./... | grep -v tls) -v $DISABLE_Ed25519_TEST
  # Check that signature functions have parity between boring and notboring
  CGO_ENABLED=0 go test $(go list ./... | grep -v tls) -v $DISABLE_Ed25519_TEST
popd
# Run all FIPS specific TLS tests
pushd crypto/tls
  go test -v -run "Boring" $DISABLE_Ed25519_TEST
popd
%else
./run.bash --no-rebuild -v -v -v -k || :
%endif
cd ..

%files

%doc AUTHORS CONTRIBUTORS LICENSE PATENTS
# VERSION has to be present in the GOROOT, for `go install std` to work
%doc %{goroot}/VERSION
%dir %{goroot}/doc
%doc %{goroot}/doc/*

# go files
%dir %{goroot}
%exclude %{goroot}/bin/
%exclude %{goroot}/pkg/
%exclude %{goroot}/src/
%exclude %{goroot}/doc/
%exclude %{goroot}/misc/
%exclude %{goroot}/test/
%{goroot}/*

# ensure directory ownership, so they are cleaned up if empty
%dir %{gopath}
%dir %{gopath}/src
%dir %{gopath}/src/github.com/
%dir %{gopath}/src/bitbucket.org/
%dir %{gopath}/src/code.google.com/
%dir %{gopath}/src/code.google.com/p/
%dir %{gopath}/src/golang.org
%dir %{gopath}/src/golang.org/x

# gdbinit (for gdb debugging)
%{_sysconfdir}/gdbinit.d

# prelink blacklist
%{_sysconfdir}/prelink.conf.d

%if 0%{?rhel} ==7
%{_rpmconfigdir}/macros.d/macros.golang
%endif

%files -f go-src.list src

%files -f go-docs.list docs

%files -f go-misc.list misc

%files -f go-tests.list tests

%files -f go-pkg.list bin
%{_bindir}/go
%{_bindir}/gofmt

%if %{shared}
%files -f go-shared.list shared
%endif

%if %{race}
%files -f go-race.list race
%endif

%changelog
* Sat Mar 29 2025 Thien Nguyen <nthien86@gmail.com> - 1.18.9-2
- Disable failure on tests

* Wed Jan 25 2023 Dave Dykstra <dwd@fedoraproject.org> - 1.18.9-1
- Update to 1.18.9 by doing the equivalent changes as centos8-stream.

* Wed Nov 30 2022 Dave Dykstra <dwd@fedoraproject.org> - 1.18.4-1
- Update to 1.18.4 by doing the equivalent changes as centos8-stream.

* Mon Aug  1 2022 Dave Dykstra <dwd@fedoraproject.org> - 1.17.12-1
- Update to 1.17.12 by doing the equivalent changes as centos8-stream.

* Thu Jun 30 2022 Dave Dykstra <dwd@fedoraproject.org> - 1.17.10-1
- Update to 1.17.10 by cherry-picking the commit from centos8-stream.

* Tue May 10 2022 Dave Dykstra <dwd@fedoraproject.org> - 1.17.7-1
- Update to 1.17.7, based on centos8-stream packaging except keeping
  go-srpm-macros and the "--with ignore_tests" rpmbuild option

* Thu Jan 20 2022 Dave Dykstra <dwd@fedoraproject.org> - 1.16.13-2
- Add back providing go-srpm-macros on rhel 7

* Tue Jan 18 2022 Dave Dykstra <dwd@fedoraproject.org> - 1.16.13-1
- Update to go1.16.13, copied from f35

* Tue Jul 27 2021 Jakub Čajka <jcajka@redhat.com> - 1.15.14-1
- Update to go1.15.14
- Fix crash in VDSO calls on ppc64le
- Security fix for CVE-2020-28851, CVE-2020-28852, CVE-2021-3114, CVE-2021-3115, CVE-2021-27918, CVE-2021-31525, CVE-2021-33198, CVE-2021-33197, CVE-2021-33195 and CVE-2021-34558
- Resolves: BZ#1913336, BZ#1913365, BZ#1918752, BZ#1918762, BZ#1937902, BZ#1958342, BZ#1989576, BZ#1989571, BZ#1989565 and BZ#1986200

* Mon Nov 16 2020 Jakub Čajka <jcajka@redhat.com> - 1.15.5-1
- Rebase to go1.15.5
- Security fix for CVE-2020-28362, CVE-2020-28367 and CVE-2020-28366
- Resolves: BZ#1897637, BZ#1897645 and BZ#1897648

* Thu Sep 10 2020 Jakub Čajka <jcajka@redhat.com> - 1.15.2-1
- Rebase to go1.15.2
- Security fix for CVE-2020-24553
- Resolves: BZ#1874859

* Tue Aug 25 2020 Jakub Čajka <jcajka@redhat.com> - 1.15-1
- Rebase to go1.15
- Security fix for CVE-2020-16845 and CVE-2020-14040
- Resolves BZ#1867100 and BZ#1853654

* Mon Jul 20 2020 Jakub Čajka <jcajka@redhat.com> - 1.13.14-1
- Rebase to go1.13.14
- Fix for  CVE-2020-15586
- Resolves: BZ#1856956

* Mon May 18 2020 Álex Sáez <asm@redhat.com> - 1.13.11-1
- Rebase to go1.13.11

* Mon Feb 03 2020 Jakub Čajka <jcajka@redhat.com> - 1.13.6-1
- Rebase to go1.13.6

* Wed Nov 13 2019 Jakub Čajka <jcajka@redhat.com> - 1.13.4-1
- Rebase to go1.13.4

* Wed Oct 30 2019 Jakub Čajka <jcajka@redhat.com> - 1.13.3-1
- Rebase to go1.13.3
- Fix for CVE-2019-17596
- Resolves: BZ#1763311

* Sat Oct 5 2019 Jakub Čajka <jcajka@redhat.com> - 1.13.1-1
- Rebase to go1.13.1
- Fix for CVE-2019-16276
- Resolves: BZ#1755971

* Tue Sep 10 2019 Jakub Čajka <jcajka@redhat.com> - 1.13-1
- Rebase to go1.13
- Fix for CVE-2019-9512, CVE-2019-9514, CVE-2019-14809
- Resolves: BZ#1741815, BZ#1741826, BZ#1743130

* Thu Aug 08 2019 Jakub Čajka <jcajka@redhat.com> - 1.11.12-1
- Rebase to 1.11.12

* Mon Feb 04 2019 Jakub Čajka <jcajka@redhat.com> - 1.11.5-1
- Rebase to go1.11.5
- Fix for CVE-2019-6486
- Resolves: BZ#1668975

* Wed Jan 02 2019 Jakub Čajka <jcajka@redhat.com> - 1.11.4-1
- Rebase to go1.11.4
- Fix for CVE-2018-16875, CVE-2018-16874 and CVE-2018-16873
- Resolves: BZ#1664332

* Fri Nov 30 2018 Jakub Čajka <jcajka@redhat.com> - 1.11.2-3
- add ppc64le proper

* Mon Nov 26 2018 Jakub Čajka <jcajka@redhat.com> - 1.11.2-2
- fix up macros file for aarch64

* Fri Nov 23 2018 Jakub Čajka <jcajka@redhat.com> - 1.11.2-1
- Rebase to go1.11.2

* Sun Oct 07 2018 Jakub Čajka <jcajka@redhat.com> - 1.11.1-1
- Rebase to go1.11.1

* Mon Jun 11 2018 Jakub Čajka <jcajka@redhat.com> - 1.9.7-1
- Rebase to 1.9.7

* Thu May 10 2018 Jakub Čajka <jcajka@redhat.com> - 1.9.6-1
- Rebase to 1.9.6

* Tue Mar 20 2018 Jakub Čajka <jcajka@redhat.com> - 1.9.4-1
- Rebase to 1.9.4
- Fix CVE-2018-6574 and CVE-2018-7187
- Resolves: BZ#1543561, BZ#1543563, BZ#1546386, BZ#1546387

* Thu Oct 26 2017 Jakub Čajka <jcajka@redhat.com> - 1.9.2-1
- Rebase to 1.9.2
- execute correctly pie tests
- allow to ignore tests via bcond
- reduce size of golang package

* Fri Oct 06 2017 Jakub Čajka <jcajka@redhat.com> - 1.9.1-1
- fix CVE-2017-15041 and CVE-2017-15042

* Fri Sep 15 2017 Jakub Čajka <jcajka@redhat.com> - 1.9-1
- bump to the relased version

* Wed Aug 02 2017 Fedora Release Engineering <releng@fedoraproject.org> - 1.9-0.beta2.1.2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_27_Binutils_Mass_Rebuild

* Wed Jul 26 2017 Fedora Release Engineering <releng@fedoraproject.org> - 1.9-0.beta2.1.1
- Rebuilt for https://fedoraproject.org/wiki/Fedora_27_Mass_Rebuild

* Tue Jul 11 2017 Jakub Čajka <jcajka@redhat.com> - 1.9-0.beta2.1
- bump to beta2

* Thu May 25 2017 Jakub Čajka <jcajka@redhat.com> - 1.8.3-1
- bump to 1.8.3
- fix for CVE-2017-8932
- make possible to use 31bit OID in ASN1
- Resolves: BZ#1454978, BZ#1455191

* Fri Apr 21 2017 Jakub Čajka <jcajka@redhat.com> - 1.8.1-2
- fix uint64 constant codegen on s390x
- Resolves: BZ#1441078

* Tue Apr 11 2017 Jakub Čajka <jcajka@redhat.com> - 1.8.1-1
- bump to Go 1.8.1
- Resolves: BZ#1440345

* Fri Feb 24 2017 Jakub Čajka <jcajka@redhat.com> - 1.8-2
- avoid possibly stale packages due to chacha test file not being test file

* Fri Feb 17 2017 Jakub Čajka <jcajka@redhat.com> - 1.8-1
- bump to released version
- Resolves: BZ#1423637
- Related: BZ#1411242

* Fri Feb 10 2017 Fedora Release Engineering <releng@fedoraproject.org> - 1.8-0.rc3.2.1
- Rebuilt for https://fedoraproject.org/wiki/Fedora_26_Mass_Rebuild

* Fri Jan 27 2017 Jakub Čajka <jcajka@redhat.com> - 1.8-0.rc3.2
- make possible to override default traceback level at build time
- add sub-package race containing std lib built with -race enabled
- Related: BZ#1411242

* Fri Jan 27 2017 Jakub Čajka <jcajka@redhat.com> - 1.8-0.rc3.1
- rebase to go1.8rc3
- Resolves: BZ#1411242

* Fri Jan 20 2017 Jakub Čajka <jcajka@redhat.com> - 1.7.4-2
- Resolves: BZ#1404679
- expose IfInfomsg.X__ifi_pad on s390x

* Fri Dec 02 2016 Jakub Čajka <jcajka@redhat.com> - 1.7.4-1
- Bump to 1.7.4
- Resolves: BZ#1400732

* Thu Nov 17 2016 Tom Callaway <spot@fedoraproject.org> - 1.7.3-2
- re-enable the NIST P-224 curve

* Thu Oct 20 2016 Jakub Čajka <jcajka@redhat.com> - 1.7.3-1
- Resolves: BZ#1387067 - golang-1.7.3 is available
- added fix for tests failing with latest tzdata

* Fri Sep 23 2016 Jakub Čajka <jcajka@redhat.com> - 1.7.1-2
- fix link failure due to relocation overflows on PPC64X

* Thu Sep 08 2016 Jakub Čajka <jcajka@redhat.com> - 1.7.1-1
- rebase to 1.7.1
- Resolves: BZ#1374103

* Tue Aug 23 2016 Jakub Čajka <jcajka@redhat.com> - 1.7-1
- update to released version
- related: BZ#1342090, BZ#1357394

* Mon Aug 08 2016 Jakub Čajka <jcajka@redhat.com> - 1.7-0.3.rc5
- Obsolete golang-vet and golang-cover from golang-googlecode-tools package
  vet/cover binaries are provided by golang-bin rpm (thanks to jchaloup)
- clean up exclusive arch after s390x boostrap
- resolves: #1268206

* Wed Aug 03 2016 Jakub Čajka <jcajka@redhat.com> - 1.7-0.2.rc5
- rebase to go1.7rc5
- Resolves: BZ#1342090

* Thu Jul 21 2016 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1.7-0.1.rc2
- https://fedoraproject.org/wiki/Changes/golang1.7

* Tue Jul 19 2016 Jakub Čajka <jcajka@redhat.com> - 1.7-0.0.rc2
- rebase to 1.7rc2
- added s390x build
- improved shared lib packaging
- Resolves: bz1357602 - CVE-2016-5386
- Resolves: bz1342090, bz1342090

* Tue Apr 26 2016 Jakub Čajka <jcajka@redhat.com> - 1.6.2-1
- rebase to 1.6.2
- Resolves: bz1329206 - golang-1.6.2.src is available

* Wed Apr 13 2016 Jakub Čajka <jcajka@redhat.com> - 1.6.1-1
- rebase to 1.6.1
- Resolves: bz1324344 - CVE-2016-3959
- Resolves: bz1324951 - prelink is gone, /etc/prelink.conf.d/* is no longer used
- Resolves: bz1326366 - wrong epoll_event struct for ppc64le/ppc64

* Mon Feb 22 2016 Jakub Čajka <jcajka@redhat.com> - 1.6-1
- Resolves: bz1304701 - rebase to go1.6 release
- Resolves: bz1304591 - fix possible stack miss-alignment in callCgoMmap

* Wed Feb 03 2016 Fedora Release Engineering <releng@fedoraproject.org> - 1.6-0.3.rc1
- Rebuilt for https://fedoraproject.org/wiki/Fedora_24_Mass_Rebuild

* Fri Jan 29 2016 Jakub Čajka <jcajka@redhat.com> - 1.6-0.2.rc1
- disabled cgo and external linking on ppc64

* Thu Jan 28 2016 Jakub Čajka <jcajka@redhat.com> - 1.6-0.1.rc1
- Resolves bz1292640, rebase to pre-release 1.6
- bootstrap for PowerPC
- fix rpmlint errors/warning

* Thu Jan 14 2016 Jakub Čajka <jcajka@redhat.com> - 1.5.3-1
- rebase to 1.5.3
- resolves bz1293451, CVE-2015-8618
- apply timezone patch, avoid using bundled data
- print out rpm build system info

* Fri Dec 11 2015 Jakub Čajka <jcajka@redhat.com> - 1.5.2-2
- bz1290543 Accept x509 certs with negative serial

* Tue Dec 08 2015 Jakub Čajka <jcajka@redhat.com> - 1.5.2-1
- bz1288263 rebase to 1.5.2
- spec file clean up
- added build options
- scrubbed "Project Gutenberg License"

* Mon Oct 19 2015 Vincent Batts <vbatts@fedoraproject.org> - 1.5.1-1
- bz1271709 include patch from upstream fix

* Wed Sep 09 2015 Vincent Batts <vbatts@fedoraproject.org> - 1.5.1-0
- update to go1.5.1

* Fri Sep 04 2015 Vincent Batts <vbatts@fedoraproject.org> - 1.5-8
- bz1258166 remove srpm macros, for go-srpm-macros

* Thu Sep 03 2015 Vincent Batts <vbatts@fedoraproject.org> - 1.5-7
- bz1258166 remove srpm macros, for go-srpm-macros

* Thu Aug 27 2015 Vincent Batts <vbatts@fedoraproject.org> - 1.5-6
- starting a shared object subpackage. This will be x86_64 only until upstream supports more arches shared objects.

* Thu Aug 27 2015 Vincent Batts <vbatts@fedoraproject.org> - 1.5-5
- bz991759 gdb path fix

* Wed Aug 26 2015 Vincent Batts <vbatts@fedoraproject.org> - 1.5-4
- disable shared object until linux/386 is ironned out
- including the test/ directory for tests

* Tue Aug 25 2015 Vincent Batts <vbatts@fedoraproject.org> - 1.5-3
- bz1256910 only allow the golang zoneinfo.zip to be used in tests
- bz1166611 add golang.org/x directory
- bz1256525 include stdlib shared object. This will let other libraries and binaries
  build with `go build -buildmode=shared -linkshared ...` or similar.

* Sun Aug 23 2015 Peter Robinson <pbrobinson@fedoraproject.org> 1.5-2
- Enable aarch64
- Minor cleanups

* Thu Aug 20 2015 Vincent Batts <vbatts@fedoraproject.org> - 1.5-1
- updating to go1.5

* Thu Aug 06 2015 Vincent Batts <vbatts@fedoraproject.org> - 1.5-0.11.rc1
- fixing the sources reference

* Thu Aug 06 2015 Vincent Batts <vbatts@fedoraproject.org> - 1.5-0.10.rc1
- updating to go1.5rc1
- checks are back in place

* Tue Aug 04 2015 Vincent Batts <vbatts@fedoraproject.org> - 1.5-0.9.beta3
- pull in upstream archive/tar fix

* Thu Jul 30 2015 Vincent Batts <vbatts@fedoraproject.org> - 1.5-0.8.beta3
- updating to go1.5beta3

* Thu Jul 30 2015 Vincent Batts <vbatts@fedoraproject.org> - 1.5-0.7.beta2
- add the patch ..

* Thu Jul 30 2015 Vincent Batts <vbatts@fedoraproject.org> - 1.5-0.6.beta2
- increase ELFRESERVE (bz1248071)

* Tue Jul 28 2015 Lokesh Mandvekar <lsm5@fedoraproject.org> - 1.5-0.5.beta2
- correct package version and release tags as per naming guidelines

* Fri Jul 17 2015 Vincent Batts <vbatts@fedoraproject.org> - 1.4.99-4.1.5beta2
- adding test output, for visibility

* Fri Jul 10 2015 Vincent Batts <vbatts@fedoraproject.org> - 1.4.99-3.1.5beta2
- updating to go1.5beta2

* Fri Jul 10 2015 Vincent Batts <vbatts@fedoraproject.org> - 1.4.99-2.1.5beta1
- add checksum to sources and fixed one patch

* Fri Jul 10 2015 Vincent Batts <vbatts@fedoraproject.org> - 1.4.99-1.1.5beta1
- updating to go1.5beta1

* Wed Jun 17 2015 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1.4.2-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_23_Mass_Rebuild

* Wed Mar 18 2015 Vincent Batts <vbatts@fedoraproject.org> - 1.4.2-2
- obsoleting deprecated packages

* Wed Feb 18 2015 Vincent Batts <vbatts@fedoraproject.org> - 1.4.2-1
- updating to go1.4.2

* Fri Jan 16 2015 Vincent Batts <vbatts@fedoraproject.org> - 1.4.1-1
- updating to go1.4.1

* Fri Jan 02 2015 Vincent Batts <vbatts@fedoraproject.org> - 1.4-2
- doc organizing

* Thu Dec 11 2014 Vincent Batts <vbatts@fedoraproject.org> - 1.4-1
- update to go1.4 release

* Wed Dec 03 2014 Vincent Batts <vbatts@fedoraproject.org> - 1.3.99-3.1.4rc2
- update to go1.4rc2

* Mon Nov 17 2014 Vincent Batts <vbatts@fedoraproject.org> - 1.3.99-2.1.4rc1
- update to go1.4rc1

* Thu Oct 30 2014 Vincent Batts <vbatts@fedoraproject.org> - 1.3.99-1.1.4beta1
- update to go1.4beta1

* Thu Oct 30 2014 Vincent Batts <vbatts@fedoraproject.org> - 1.3.3-3
- macros will need to be in their own rpm

* Fri Oct 24 2014 Vincent Batts <vbatts@fedoraproject.org> - 1.3.3-2
- split out rpm macros (bz1156129)
- progress on gccgo accomodation

* Wed Oct 01 2014 Vincent Batts <vbatts@fedoraproject.org> - 1.3.3-1
- update to go1.3.3 (bz1146882)

* Mon Sep 29 2014 Vincent Batts <vbatts@fedoraproject.org> - 1.3.2-1
- update to go1.3.2 (bz1147324)

* Thu Sep 11 2014 Vincent Batts <vbatts@fedoraproject.org> - 1.3.1-3
- patching the tzinfo failure

* Sat Aug 16 2014 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1.3.1-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_21_22_Mass_Rebuild

* Wed Aug 13 2014 Vincent Batts <vbatts@fedoraproject.org> - 1.3.1-1
- update to go1.3.1

* Wed Aug 13 2014 Vincent Batts <vbatts@fedoraproject.org> - 1.3-11
- merged a line wrong

* Wed Aug 13 2014 Vincent Batts <vbatts@fedoraproject.org> - 1.3-10
- more work to get cgo.a timestamps to line up, due to build-env
- explicitly list all the files and directories for the source and packages trees
- touch all the built archives to be the same

* Mon Aug 11 2014 Vincent Batts <vbatts@fedoraproject.org> - 1.3-9
- make golang-src 'noarch' again, since that was not a fix, and takes up more space

* Mon Aug 11 2014 Vincent Batts <vbatts@fedoraproject.org> - 1.3-8
- update timestamps of source files during %%install bz1099206

* Fri Aug 08 2014 Vincent Batts <vbatts@fedoraproject.org> - 1.3-7
- update timestamps of source during %%install bz1099206

* Wed Aug 06 2014 Vincent Batts <vbatts@fedoraproject.org> - 1.3-6
- make the source subpackage arch'ed, instead of noarch

* Mon Jul 21 2014 Vincent Batts <vbatts@fedoraproject.org> - 1.3-5
- fix the writing of pax headers

* Tue Jul 15 2014 Vincent Batts <vbatts@fedoraproject.org> - 1.3-4
- fix the loading of gdb safe-path. bz981356

* Tue Jul 08 2014 Vincent Batts <vbatts@fedoraproject.org> - 1.3-3
- `go install std` requires gcc, to build cgo. bz1105901, bz1101508

* Mon Jul 07 2014 Vincent Batts <vbatts@fedoraproject.org> - 1.3-2
- archive/tar memory allocation improvements

* Thu Jun 19 2014 Vincent Batts <vbatts@fedoraproject.org> - 1.3-1
- update to go1.3

* Fri Jun 13 2014 Vincent Batts <vbatts@fedoraproject.org> - 1.3rc2-1
- update to go1.3rc2

* Sat Jun 07 2014 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1.3rc1-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_21_Mass_Rebuild

* Tue Jun 03 2014 Vincent Batts <vbatts@redhat.com> 1.3rc1-1
- update to go1.3rc1
- new arch file shuffling

* Wed May 21 2014 Vincent Batts <vbatts@redhat.com> 1.3beta2-1
- update to go1.3beta2
- no longer provides go-mode for xemacs (emacs only)

* Wed May 21 2014 Vincent Batts <vbatts@redhat.com> 1.2.2-7
- bz1099206 ghost files are not what is needed

* Tue May 20 2014 Vincent Batts <vbatts@redhat.com> 1.2.2-6
- bz1099206 more fixing. The packages %%post need golang-bin present first

* Tue May 20 2014 Vincent Batts <vbatts@redhat.com> 1.2.2-5
- bz1099206 more fixing. Let go fix its own timestamps and freshness

* Tue May 20 2014 Vincent Batts <vbatts@redhat.com> 1.2.2-4
- fix the existence and alternatives of `go` and `gofmt`

* Mon May 19 2014 Vincent Batts <vbatts@redhat.com> 1.2.2-3
- bz1099206 fix timestamp issue caused by koji builders

* Fri May 09 2014 Vincent Batts <vbatts@redhat.com> 1.2.2-2
- more arch file shuffling

* Fri May 09 2014 Vincent Batts <vbatts@redhat.com> 1.2.2-1
- update to go1.2.2

* Thu May 08 2014 Vincent Batts <vbatts@redhat.com> 1.2.1-8
- RHEL6 rpm macros can't %%exlude missing files

* Wed May 07 2014 Vincent Batts <vbatts@redhat.com> 1.2.1-7
- missed two arch-dependent src files

* Wed May 07 2014 Vincent Batts <vbatts@redhat.com> 1.2.1-6
- put generated arch-dependent src in their respective RPMs

* Fri Apr 11 2014 Vincent Batts <vbatts@redhat.com> 1.2.1-5
- skip test that is causing a SIGABRT on fc21 bz1086900

* Thu Apr 10 2014 Vincent Batts <vbatts@fedoraproject.org> 1.2.1-4
- fixing file and directory ownership bz1010713

* Wed Apr 09 2014 Vincent Batts <vbatts@fedoraproject.org> 1.2.1-3
- including more to macros (%%go_arches)
- set a standard goroot as /usr/lib/golang, regardless of arch
- include sub-packages for compiler toolchains, for all golang supported architectures

* Wed Mar 26 2014 Vincent Batts <vbatts@fedoraproject.org> 1.2.1-2
- provide a system rpm macros. Starting with gopath

* Tue Mar 04 2014 Adam Miller <maxamillion@fedoraproject.org> 1.2.1-1
- Update to latest upstream

* Thu Feb 20 2014 Adam Miller <maxamillion@fedoraproject.org> 1.2-7
- Remove  _BSD_SOURCE and _SVID_SOURCE, they are deprecated in recent
  versions of glibc and aren't needed

* Wed Feb 19 2014 Adam Miller <maxamillion@fedoraproject.org> 1.2-6
- pull in upstream archive/tar implementation that supports xattr for
  docker 0.8.1

* Tue Feb 18 2014 Vincent Batts <vbatts@redhat.com> 1.2-5
- provide 'go', so users can yum install 'go'

* Fri Jan 24 2014 Vincent Batts <vbatts@redhat.com> 1.2-4
- skip a flaky test that is sporadically failing on the build server

* Thu Jan 16 2014 Vincent Batts <vbatts@redhat.com> 1.2-3
- remove golang-godoc dependency. cyclic dependency on compiling godoc

* Wed Dec 18 2013 Vincent Batts <vbatts@redhat.com> - 1.2-2
- removing P224 ECC curve

* Mon Dec 2 2013 Vincent Batts <vbatts@fedoraproject.org> - 1.2-1
- Update to upstream 1.2 release
- remove the pax tar patches

* Tue Nov 26 2013 Vincent Batts <vbatts@redhat.com> - 1.1.2-8
- fix the rpmspec conditional for rhel and fedora

* Thu Nov 21 2013 Vincent Batts <vbatts@redhat.com> - 1.1.2-7
- patch tests for testing on rawhide
- let the same spec work for rhel and fedora

* Wed Nov 20 2013 Vincent Batts <vbatts@redhat.com> - 1.1.2-6
- don't symlink /usr/bin out to ../lib..., move the file
- seperate out godoc, to accomodate the go.tools godoc

* Fri Sep 20 2013 Adam Miller <maxamillion@fedoraproject.org> - 1.1.2-5
- Pull upstream patches for BZ#1010271
- Add glibc requirement that got dropped because of meta dep fix

* Fri Aug 30 2013 Adam Miller <maxamillion@fedoraproject.org> - 1.1.2-4
- fix the libc meta dependency (thanks to vbatts [at] redhat.com for the fix)

* Tue Aug 27 2013 Adam Miller <maxamillion@fedoraproject.org> - 1.1.2-3
- Revert incorrect merged changelog

* Tue Aug 27 2013 Adam Miller <maxamillion@fedoraproject.org> - 1.1.2-2
- This was reverted, just a placeholder changelog entry for bad merge

* Tue Aug 20 2013 Adam Miller <maxamillion@fedoraproject.org> - 1.1.2-1
- Update to latest upstream

* Sat Aug 03 2013 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1.1.1-7
- Rebuilt for https://fedoraproject.org/wiki/Fedora_20_Mass_Rebuild

* Wed Jul 17 2013 Petr Pisar <ppisar@redhat.com> - 1.1.1-6
- Perl 5.18 rebuild

* Wed Jul 10 2013 Adam Goode <adam@spicenitz.org> - 1.1.1-5
- Blacklist testdata files from prelink
- Again try to fix #973842

* Fri Jul  5 2013 Adam Goode <adam@spicenitz.org> - 1.1.1-4
- Move src to libdir for now (#973842) (upstream issue https://code.google.com/p/go/issues/detail?id=5830)
- Eliminate noarch data package to work around RPM bug (#975909)
- Try to add runtime-gdb.py to the gdb safe-path (#981356)

* Wed Jun 19 2013 Adam Goode <adam@spicenitz.org> - 1.1.1-3
- Use lua for pretrans (http://fedoraproject.org/wiki/Packaging:Guidelines#The_.25pretrans_scriptlet)

* Mon Jun 17 2013 Adam Goode <adam@spicenitz.org> - 1.1.1-2
- Hopefully really fix #973842
- Fix update from pre-1.1.1 (#974840)

* Thu Jun 13 2013 Adam Goode <adam@spicenitz.org> - 1.1.1-1
- Update to 1.1.1
- Fix basically useless package (#973842)

* Sat May 25 2013 Dan Horák <dan[at]danny.cz> - 1.1-3
- set ExclusiveArch

* Fri May 24 2013 Adam Goode <adam@spicenitz.org> - 1.1-2
- Fix noarch package discrepancies

* Fri May 24 2013 Adam Goode <adam@spicenitz.org> - 1.1-1
- Initial Fedora release.
- Update to 1.1

* Thu May  9 2013 Adam Goode <adam@spicenitz.org> - 1.1-0.3.rc3
- Update to rc3

* Thu Apr 11 2013 Adam Goode <adam@spicenitz.org> - 1.1-0.2.beta2
- Update to beta2

* Tue Apr  9 2013 Adam Goode <adam@spicenitz.org> - 1.1-0.1.beta1
- Initial packaging.
