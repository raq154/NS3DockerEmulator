#!/bin/sh

# This file basically destroy the network bridge and TAP interface

if [ -z "$1" ]
  then
    echo "No name supplied"
    exit 1
fi

NAME=$1

ifconfig br-$NAME down

brctl delif br-$NAME tap-$NAME

brctl delbr br-$NAME

ifconfig tap-$NAME down

tunctl -d tap-$NAME

if [ 1 -eq 0 ]; then
  ifconfig br-left down
  ifconfig br-right down
  brctl delif br-left tap-left
  brctl delif br-right tap-right
  brctl delbr br-left
  brctl delbr br-right
  ifconfig tap-left down
  ifconfig tap-right down
  tunctl -d tap-left
  tunctl -d tap-right
fi
