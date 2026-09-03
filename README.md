### Setting up the CentOS 6 environment with Docker and build

Use Docker to setting up a CentOS 6 environemnt with following command:

```
docker run -it -d library/centos:6.10 bash
```

And run following commands inside the container:

```
rm -f /etc/yum.repos.d/*.repo

cat << 'EOF' > /etc/yum.repos.d/CentOS-Base.repo
[base]
name=CentOS-6.10 - Base Archive
baseurl=https://archive.kernel.org/centos-vault/6.10/os/x86_64/
gpgcheck=1
gpgkey=https://archive.kernel.org/centos-vault/RPM-GPG-KEY-CentOS-6
enabled=1

[updates]
name=CentOS-6.10 - Updates Archive
baseurl=https://archive.kernel.org/centos-vault/6.10/updates/x86_64/
gpgcheck=1
gpgkey=https://archive.kernel.org/centos-vault/RPM-GPG-KEY-CentOS-6
enabled=1

[extras]
name=CentOS-6.10 - Extras Archive
baseurl=https://archive.kernel.org/centos-vault/6.10/extras/x86_64/
gpgcheck=1
gpgkey=https://archive.kernel.org/centos-vault/RPM-GPG-KEY-CentOS-6
enabled=1
EOF

yum install -y git rpmdevtools yum-utils

git clone -b el6 https://github.com/shatteredsilicon/golang.git ~/golang && cd ~/golang
spectool -C ./rpmbuild/SOURCES -g golang.spec
rpmbuild -ba --define "_topdir `pwd`/rpmbuild" golang.spec
```

And finally the golang package should be located in `~/golang/rpmbuild/RPMS/x86_64/golang-bin-1.26.8-1.el6.x86_64.rpm` if all these preceding commands were executed successfully.