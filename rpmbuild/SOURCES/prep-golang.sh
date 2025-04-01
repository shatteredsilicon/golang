#!/bin/bash

set -e

GO_VERSION="1.24.1"
GO_FS_VERSION="3.6.0"

rm -f *.tar.gz

wget https://go.dev/dl/go${GO_VERSION}.src.tar.gz
wget https://pagure.io/go-rpm-macros/archive/${GO_FS_VERSION}/go-rpm-macros-${GO_FS_VERSION}.tar.gz
