#!/bin/bash

curl -o /usr/bin/receptor.tgz -L https://github.com/ansible/receptor/releases/download/v1.4.8/receptor_1.4.8_linux_arm64.tar.gz
tar -xzf /usr/bin/receptor.tgz -C /usr/bin
pip install receptorctl
exec $@
