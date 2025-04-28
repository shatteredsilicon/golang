Golang packaging for rhel and debian-based.

Since incremental version bootstrap for el7 is required, includes golang versions:
- 1.18.9
- 1.20.12
- 1.23.4
- 1.24.1

#### Prerequisites

- wget
- tar
- build-essential (for deb)
- rpmdevtools (for rpm)

And use following command to install prerequisites automatically for building

##### RPM

```
yum-builddep rpmbuild/SPECS/golang.spec
```

##### DEB

```
mk-build-deps --install debian/control
```

>
> Tips: for debian 12- that doesn't have golang-1.22+ in default repos, you can use the bookworm-backport repo with:
> `echo 'deb http://deb.debian.org/debian bookworm-backports main' > /etc/apt/sources.list.d/bookworm-backports.list` 
>

#### build

Run
```
./all.sh
```
