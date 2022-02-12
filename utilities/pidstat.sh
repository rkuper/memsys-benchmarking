#!/bin/bash

pidstat --human -u -w -r -d -p $1 1 >pidstat.out
