Name:           golang-bin
Version:        1.26.8
Release:        1%{?dist}
Summary:        Go programming language pre-compiled binaries from go.dev
License:        BSD
URL:            https://go.dev

Source0:        https://go.dev/dl/go%{version}.linux-amd64.tar.gz

# Tell RPM not to strip the already compiled Go binaries or alter their build IDs
%define __spec_install_post %{nil}
%define __os_install_post %{nil}
%define debug_package %{nil}

# Disable automatic dependency generation to avoid glibc version requirement spikes
AutoReqProv: no

Provides:       go = %{version}
Provides:       golang = %{version}

%description
This package contains the official, pre-compiled Linux x86_64 binaries 
for the Go programming language, packaged directly from go.dev.

%prep
# -b 0 tells %setup not to unpack Source0 before entering the directory, 
# since we want to extract it manually inside our custom structure.
%setup -c -T -b 0

%build
tar -xzf %{SOURCE0}

%install
rm -rf %{buildroot}

mkdir -p %{buildroot}/usr/local/go
mkdir -p %{buildroot}/usr/bin

cp -r go/* %{buildroot}/usr/local/go/

ln -sf /usr/local/go/bin/go %{buildroot}/usr/bin/go
ln -sf /usr/local/go/bin/gofmt %{buildroot}/usr/bin/gofmt

%clean
rm -rf %{buildroot}

%files
%defattr(-,root,root,-)
/usr/local/go/
/usr/bin/go
/usr/bin/gofmt

%changelog
