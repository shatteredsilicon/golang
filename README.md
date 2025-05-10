Golang packaging for rhel and debian-based.

Since incremental version bootstrap for el7 is required, includes golang versions:
- 1.18.9
- 1.20.12
- 1.23.4
- 1.24.1

#### Prerequisites

##### DEB

Use following commands to install prerequisites

>
> Tips: for debian 12- that doesn't have golang-1.22+ in default repos, you can use the bookworm-backport repo with:
> `echo 'deb http://deb.debian.org/debian bookworm-backports main' > /etc/apt/sources.list.d/bookworm-backports.list` 
>

```
apt update
apt install wget tar build-essential devscripts
mk-build-deps --install debian/control
```

##### RPM

Use following commands to install prerequisites

```
yum install wget tar rpmdevtools yum-utils
yum-builddep rpmbuild/SPECS/golang.spec
```

#### Build

Run
```
./all.sh
```
