#!/usr/env bash
cd /var/lib/mongodb
sudo rm mongod.lock
sudo -u mongodb /usr/bin/mongod -f /etc/mongodb.conf --repair
mongod -dbpath=/var/lib/mongodb -logpath=/var/log/
sudo start mongodb