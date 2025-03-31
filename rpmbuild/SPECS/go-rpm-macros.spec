%global forgeurl  https://pagure.io/go-rpm-macros
Version:   3.6.0

%global debug_package %{nil}

#https://src.fedoraproject.org/rpms/redhat-rpm-config/pull-request/51
%global _spectemplatedir %{_datadir}/rpmdevtools/fedora
%global _docdir_fmt     %{name}

# Master definition that will be written to macro files
%global golang_arches_future x86_64 %{arm} aarch64 ppc64le s390x riscv64
%global golang_arches   %{ix86} %{golang_arches_future}
%global gccgo_arches    %{mips}
%if 0%{?rhel} >= 9
%global golang_arches   x86_64 aarch64 ppc64le s390x
%endif
%if 0%{?rhel} >= 10
%global golang_arches   x86_64 aarch64 ppc64le s390x riscv64
%endif
# Go sources can contain arch-specific files and our macros will package the
# correct files for each architecture. Therefore, move gopath to _libdir and
# make Go devel packages archful
%global gopath          %{_datadir}/gocode

%{!?rpmmacrodir: %global rpmmacrodir /usr/lib/rpm/macros.d}
%{!?rpmluadir: %global rpmluadir /usr/lib/rpm/lua}

Name:      go-rpm-macros
Release:   2%{?dist}
Summary:   Build-stage rpm automation for Go packages

License:   GPL-3.0-or-later
URL:       %{forgeurl}
Source0:   go-rpm-macros-%{version}.tar.gz

Requires:  go-srpm-macros = %{version}-%{release}
Requires:  go-filesystem  = %{version}-%{release}
Requires:  golist

%ifarch %{golang_arches}
Requires:  golang
Provides:  compiler(golang)
Provides:  compiler(go-compiler) = 2
Obsoletes: go-compilers-golang-compiler < %{version}-%{release}
%endif

%ifarch %{gccgo_arches}
Requires:  gcc-go
Provides:  compiler(gcc-go)
Provides:  compiler(go-compiler) = 1
Obsoletes: go-compilers-gcc-go-compiler < %{version}-%{release}
%endif

%description
This package provides build-stage rpm automation to simplify the creation of Go
language (golang) packages.

It does not need to be included in the default build root: go-srpm-macros will
pull it in for Go packages only.

%package -n go-srpm-macros
Summary:   Source-stage rpm automation for Go packages
BuildArch: noarch
Requires:  redhat-rpm-config
# macros.forge and forge.lua were split into a separate package.
# redhat-rpm-config pulls in forge-srpm-macros but better to explicitly Require
# it.
%if (0%{?fedora} >= 40 || 0%{?rhel} >= 10)
Requires:  forge-srpm-macros
%endif

%description -n go-srpm-macros
This package provides SRPM-stage rpm automation to simplify the creation of Go
language (golang) packages.

It limits itself to the automation subset required to create Go SRPM packages
and needs to be included in the default build root.

The rest of the automation is provided by the go-rpm-macros package, that
go-srpm-macros will pull in for Go packages only.

%package -n go-filesystem
Summary:   Directories used by Go packages
License:   LicenseRef-Fedora-Public-Domain

%description -n go-filesystem
This package contains the basic directory layout used by Go packages.

%package -n go-rpm-templates
Summary:   RPM spec templates for Go packages
License:   MIT
# go-rpm-macros only exists on some architectures, so this package cannot be noarch
Requires:  go-rpm-macros = %{version}-%{release}
#https://src.fedoraproject.org/rpms/redhat-rpm-config/pull-request/51
#Requires:  redhat-rpm-templates

%description -n go-rpm-templates
This package contains documented rpm spec templates showcasing how to use the
macros provided by go-rpm-macros to create Go packages.

%prep
%setup -q
mkdir -p rpm/macros.d
cat <<EOF > rpm/macros.d/macros.go-srpm
%global golang_arches %{golang_arches}
%global golang_arches_future %{golang_arches_future}
%global gccgo_arches %{gccgo_arches}
%global gopath %{gopath}
EOF

for template in templates/rpm/*.spec ; do
  target=$(echo "${template}" | sed "s|^\(.*\)\.spec$|\1-bare.spec|")
  grep -v '^#' "${template}" > "${target}"
  touch -r "${template}" "${target}"
done

%install
install -m 0755 -vd   %{buildroot}%{rpmmacrodir}
install -m 0755 -vd %{buildroot}%{_rpmconfigdir}/macros.d

install -m 0755 -vd   %{buildroot}%{rpmluadir}/fedora/srpm
install -m 0644 -vp   rpm/lua/srpm/*lua \
                      %{buildroot}%{rpmluadir}/fedora/srpm

%ifarch %{golang_arches} %{gccgo_arches}
# Some of those probably do not work with gcc-go right now
# This is not intentional, but mips is not a primary Fedora architecture
# Patches and PRs are welcome

install -m 0755 -vd   %{buildroot}%{gopath}/src

install -m 0755 -vd   %{buildroot}%{_spectemplatedir}

install -m 0644 -vp   templates/rpm/*spec \
                      %{buildroot}%{_spectemplatedir}

install -m 0755 -vd   %{buildroot}%{_bindir}
install -m 0755 bin/* %{buildroot}%{_bindir}

install -m 0644 -vp   rpm/macros.d/macros.go-*rpm* \
                      %{buildroot}%{rpmmacrodir}
install -m 0755 -vd   %{buildroot}%{rpmluadir}/fedora/rpm
install -m 0644 -vp   rpm/lua/rpm/*lua \
                      %{buildroot}%{rpmluadir}/fedora/rpm
install -m 0755 -vd   %{buildroot}%{_rpmconfigdir}/fileattrs
install -m 0644 -vp   rpm/fileattrs/*.attr \
                      %{buildroot}%{_rpmconfigdir}/fileattrs/
install -m 0755 -vp   rpm/*\.{prov,deps} \
                      %{buildroot}%{_rpmconfigdir}/
%else
install -m 0644 -vp   rpm/macros.d/macros.go-srpm \
                      %{buildroot}%{rpmmacrodir}
%endif

%ifarch %{golang_arches}
install -m 0644 -vp   rpm/macros.d/macros.go-compilers-golang{,-pie} \
                      %{buildroot}%{_rpmconfigdir}/macros.d/
%endif

%ifarch %{gccgo_arches}
install -m 0644 -vp   rpm/macros.d/macros.go-compilers-gcc \
                      %{buildroot}%{_rpmconfigdir}/macros.d/
%endif

%ifarch %{golang_arches} %{gccgo_arches}
%files
%license LICENSE.txt
%doc README.md
%doc NEWS.md
%{_bindir}/*
%{_rpmconfigdir}/fileattrs/*.attr
%{_rpmconfigdir}/*.prov
%{_rpmconfigdir}/*.deps
%{rpmmacrodir}/macros.go-rpm*
%{rpmmacrodir}/macros.go-compiler*
%{rpmluadir}/fedora/rpm/*.lua

%files -n go-rpm-templates
%license LICENSE-templates.txt
%doc README.md
%doc NEWS.md
# https://src.fedoraproject.org/rpms/redhat-rpm-config/pull-request/51
%dir %{dirname:%{_spectemplatedir}}
%dir %{_spectemplatedir}
%{_spectemplatedir}/*.spec

%files -n go-filesystem
%dir %{gopath}
%dir %{gopath}/src
%endif

# we only build go-srpm-macros on all architectures
%files -n go-srpm-macros
%license LICENSE.txt
%doc README.md
%doc NEWS.md
%{rpmmacrodir}/macros.go-srpm
%{rpmluadir}/fedora/srpm/*.lua

%changelog
