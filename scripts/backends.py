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
import json
from collections import Counter
from colorama import Fore, Back, Style



"""
Manage Redis: Force redis to a specific NUMA node if need be
"""
def manage_redis(general_configs, action):
    errors = 0
    if (action == "start"):
        # Remove any backed up db files to lighten load on starting new server and prevent cloging up storage
        possible_directories = [general_configs["paths"]["script-root"], \
            general_configs["paths"]["redis-directory"], os.getcwd()]
        for directory in possible_directories:
            try:
                os.remove(directory + "/*.rdb")
            except:
                pass

        # Create command dependent on what NUMA preferences found within the configuration files
        cmd = general_configs["exe-prefixes"]["numa"]
        cmd += " " + os.path.join(general_configs["paths"]["redis-directory"], "redis-server")

        # Try running the redis-server on the desired NUMA configuration
        print_step("TOOLS", Fore.CYAN, "REDIS-START-CMD: " + cmd)
        try:
            redis_proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(2)
        except:
            print_error("Error found when running the redis-server"); errors += 1

    else:
        # Try to flush the redis server to save up a bit of memory
        try:
            subprocess.run(os.path.join(general_configs["paths"]["redis-directory"], "redis-cli") + " FLUSHALL", \
                        shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except:
            print_error("Could not flush the Redis server"); errors += 1
            return errors

        # Kill any process associated with the redis-server
        try:
            for line in os.popen("ps ax | grep redis-server | grep -v grep"):
                fields = line.split()
                pid = fields[0]
                os.kill(int(pid), signal.SIGKILL)
            time.sleep(2)
        except:
            print_error("Could not kill Redis server"); errors += 1
    return errors



"""
Helpful functions for averaging out data processing
"""
def flatten_dict(pyobj, keystring=''):
    if type(pyobj) == dict:
        keystring = keystring + '_' if keystring else keystring
        for k in pyobj:
            yield from flatten_dict(pyobj[k], keystring + str(k))
    else:
        yield keystring, pyobj


def nest_dict(dict1):
    result = {}
    for k, v in dict1.items():
        split_rec(k, v, result)
    return result


def split_rec(k, v, out):
    k, *rest = k.split('_', 1)
    if rest:
        split_rec(rest[0], v, out.setdefault(k, {}))
    else:
        out[k] = v


def average_dicts(processed_data):
    # Flatten the data processed from each sample
    flattened_processed_data = []
    for data in processed_data:
        flattened_processed_data.append({ k:v for k,v in flatten_dict(processed_data[data]) })

    # Average the data found in each sample (from flattened dictionaries)
    sums = Counter()
    counters = Counter()
    for itemset in flattened_processed_data:
        sums.update(itemset)
        counters.update(itemset.keys())

    # Covert the flattened data to nested dictionaries and dump the data to the proper results directory
    return nest_dict({x: round(float(sums[x])/counters[x], 2) for x in sums.keys()})



"""
Print statements for extra clarity
"""
def print_error(stmt):
    print(Fore.RED + "[ERROR] " + Style.RESET_ALL + stmt)

def print_warning(stmt):
    print(Fore.YELLOW + "[WARNING] " + Style.RESET_ALL + stmt)

def print_step(step, color, stmt):
    print(color + "[" + step + "] " + Style.RESET_ALL + stmt)




"""
File writing helper
"""
def write_data(data, path):
    complete_file = open(path, "w")
    json.dump(data, complete_file, indent=4)
    complete_file.close()

