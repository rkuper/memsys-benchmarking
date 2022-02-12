#!/bin/bash

rm -rf ps.out
while :; do
    ps -p $1 -ho pid,state,%cpu,%mem,sz,vsz,rsz,drs,maj_flt,min_flt >>ps.out
    sleep 1
done
