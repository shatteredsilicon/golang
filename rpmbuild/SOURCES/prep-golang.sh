#!/bin/bash

set -e

GO_VERSION="1.23.4"

rm -f *.tar.gz

wget https://go.dev/dl/go${GO_VERSION}.src.tar.gz
