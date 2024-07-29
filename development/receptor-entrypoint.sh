#!/bin/bash

curl -o /usr/bin/receptor.tgz -L https://github.com/ansible/receptor/releases/download/v1.4.8/receptor_1.4.8_linux_arm64.tar.gz
tar -xzf /usr/bin/receptor.tgz -C /usr/bin
chmod +x /usr/bin/receptor
pip install receptorctl
/usr/bin/receptor --config /etc/receptor/receptor.conf > /etc/receptor/stdout 2> /etc/receptor/stderr &
# TODO: we need to wait until the mesh is up and running, but just sleeping for 10 seconds now to get it working
sleep 10
exec $@
