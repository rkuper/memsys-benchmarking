"""""""""""""""""""""""""""""""""""""""""""""""""""
Run benchmark suites for testing memory system
===================================================
Filename: run.py
Author: Reese Kuper
Purpose: Run multiple benchmarks for memsys testing
test configurations specificied in configs.yml
"""""""""""""""""""""""""""""""""""""""""""""""""""

import os
import signal
import sys
import time
import argparse
import yaml
import numa
from benchmarks import *



"""
Parse the general YAML configurations to make sure they make sense
NOTE: May need to adjust if adding new general configurations to the YAML file
"""
def parse_general_yml(configs):
    # Check to make sure the arguments make sense
    parse_errors = 0
    found_output_directory = False

    for general in configs:
        if general == "numa-config":
            if int(configs[general]["local-node"]) > numa.get_max_node():
                print("[ERROR] local node value not in range of available NUMA nodes")
                arg_errors += 1
            elif int(configs[general]["remote-node"]) > numa.get_max_node():
                print("[ERROR] remote node value not in range of available NUMA nodes")
                arg_errors += 1
        if general == "paths":
            configs[general]["script-root"] = os.getcwd()
            if "redis-directory" in configs[general]:
                configs[general]["redis-directory"] = os.getcwd() + configs[general]["redis-directory"]
            if "output-directory" in configs[general]:
                found_output_directory = True

    if not found_output_directory:
        print("[ERROR] Could not find the output directory general entry")
        arg_errors += 1

    return parse_errors



"""
Create the results directory if needed
"""
def create_results(configs, output_directory):
    # Recreate results directory if it does not exist
    if not os.path.exists(output_directory):
        os.system("mkdir " + output_directory)
        for benchmark in configs:
            if benchmark == "general":
                continue
            os.system("mkdir " + output_directory + "/" + benchmark)
            for sub_benchmark in configs[benchmark]:
                os.system("mkdir " + output_directory + "/" + benchmark + "/" + sub_benchmark)
    else:
        for benchmark in configs:
            if benchmark == "general":
                continue
            if not os.path.exists(output_directory + "/" + benchmark):
                os.system("mkdir " + output_directory + "/" + benchmark)
                for sub_benchmark in configs[benchmark]:
                    os.system("mkdir " + output_directory + "/" + benchmark + "/" + sub_benchmark)
            else:
                for sub_benchmark in configs[benchmark]:
                    if not os.path.exists(output_directory + "/" + benchmark + "/" + sub_benchmark):
                        os.system("mkdir " + output_directory + "/" + benchmark + "/" + sub_benchmark)



"""
Build the benchmark objects for easier use and extensability
Per benchmark:
    1. Create benchmark object from the corresponding benchmark suite for the current sub-benchmark
    2. Add info (executable, path, etc.) and the execution parameters to the object
    3. Append benchmark object list with that object
"""
def build_benchmark_objects(general, configs):
    benchmarks = []
    for benchmark in configs:

        # Skip to the actual benchmarks
        if benchmark == "general":
            continue

        # Begin building objects
        for sub_benchmark in configs[benchmark]:

            # Step 1. Create needed benchmark type
            if benchmark == "tailbench":
                benchmark_i = tailbench(sub_benchmark)
            elif benchmark == "ycsb":
                benchmark_i = ycsb(sub_benchmark)
            elif benchmark == "memtier":
                benchmark_i = memtier(sub_benchmark)
            elif benchmark == "pmbench":
                benchmark_i = pmbench(sub_benchmark)
            elif benchmark == "cachebench":
                benchmark_i = cachebench(sub_benchmark)
            elif benchmark == "gapbs":
                benchmark_i = gapbs(sub_benchmark)
            else:
                print("[WARNING] Defaulting benchmark " + str(benchmark))
                benchmark_i = benchmark(sub_benchmark)

            # Step 2: Add benchmark information and parameters to benchmark object
            for info in configs[benchmark][sub_benchmark]["info"]:
                benchmark_i.add_info(info, configs[benchmark][sub_benchmark]["info"][info])
            for parameter in configs[benchmark][sub_benchmark]["parameters"]:
                if parameter in general["overwrite"]:
                    benchmark_i.add_parameter(parameter, general["overwrite"][parameter])
                else:
                    benchmark_i.add_parameter(parameter, configs[benchmark][sub_benchmark]["parameters"][parameter])

            # Append benchmark to benchmark list
            benchmarks.append(benchmark_i)
    return benchmarks



"""
Execute, process, and/or analyze each benchmark based on the set configs in the YAML file
"""
def do_benchmark_operations(general, benchmarks):
    for operation in general["operations"]:
        for benchmark in benchmarks:
            if operation == "execute" and general["operations"][operation]:
                benchmark.execute(general)
        for benchmark in benchmarks:
            if operation == "process" and general["operations"][operation]:
                benchmark.process(general)
        # I have yet to figure out what to do with this
        if operation == "analyze" and general["operations"][operation]:
            print("[WIP] Coming soon...")
    return



"""
Main: Parses and adjusts arguments passed in to ensure it matches system configs. Also
      calls execute and process functions.
"""
def main():
    # Parse arguments, ensure they make sense
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", help = \
            "Yaml configuration file for benchmarks (Default = configs.yml)", default="configs.yml")
    args = parser.parse_args()

    # Open up the yaml file and get the configurations. Report any found errors
    if not os.path.exists(args.config):
        print("[ERROR] YAML configuration file, " + args.config + ", was not found!")
        return
    yml_file = open(args.config, 'r')
    try:
        configs = yaml.safe_load(yml_file)
    except yaml.YAMLError as exception:
        print(exception)
        print("[ERROR] YAML configuration file is not formatted correctly!")
        return

    # Ensure general in yaml file makes sense
    general = configs.pop("general")
    parse_errors = parse_general_yml(general)
    if parse_errors > 0:
        print("[ERROR] Found " + str(parse_errors) + " error(s) within the YAML configuration file, " + args.config)
        return

    # Create the results directory if it is not found.
    # Output directory is guarenteed to be there by parse_general_yml()
    create_results(configs, general["paths"]["output-directory"])

    # Grab all of the benchmarks in a list
    benchmarks = build_benchmark_objects(general, configs)

    # Operate over each benchmark
    do_benchmark_operations(general, benchmarks)
    return



if __name__=="__main__":
    main()
