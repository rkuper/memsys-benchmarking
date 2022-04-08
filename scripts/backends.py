"""""""""""""""""""""""""""""""""""""""""""""""""""
Functions helpful for executing or processing
===================================================
Filename: backends.py
Author: Reese Kuper
Purpose: Functions for executing or processing
"""""""""""""""""""""""""""""""""""""""""""""""""""

import os
import subprocess
import signal
import sys
import time
import datetime
import argparse
import yaml
import numa
from colorama import Fore, Back, Style

"""
Manage Redis: Force redis to a specific NUMA node if need be
"""
def manage_redis(cpu_node, mem_node, script_root, current_directory, action):
    if (action == "start"):
        # Remove any backed up db files to lighten load on starting new server and prevent cloging up storage
        possible_directories = [script_root, redis_directory, current_directory, "../" + current_directory]
        for directory in possible_directories:
            os.remove(directory + "/*.rdb")
        time.sleep(4)

        # Start Redis on specific numa nodes for cpu and memory
        redis_start_cmd = "sudo numactl --cpunodebind=" + str(cpu_node) + " --membind=" + str(mem_node) + " redis-server"
        subprocess.Popen(redis_start_cmd, cwd=redis_directory)
        time.sleep(4)

    else:
        try:
            subprocess.run(os.path.join(redis_directory, "redis-cli") + " FLUSHALL")
        except:
            print("[ERROR] Could not flush Redis server")
            return

        try:
            for line in os.popen("ps ax | grep redis-server | grep -v grep"):
                fields = line.split()
                pid = fields[0]
                os.kill(int(pid), signal.SIGKILL)
            time.sleep(2)
        except:
            print("[ERROR] Could not kill Redis server")
    return

"""
Print statements for extra clarity
"""
def print_error(stmt):
    print(Fore.RED + "[ERROR] " + Style.RESET_ALL + stmt)

def print_warning(stmt):
    print(Fore.YELLOW + "[WARNING] " + Style.RESET_ALL + stmt)

def print_step(step, color, stmt):
    print(color + "[" + step + "] " + Style.RESET_ALL + stmt)


