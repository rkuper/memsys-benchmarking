"""""""""""""""""""""""""""""""""""""""""""""""""""
Top file for memory system tester script
===================================================
Filename: main.py
Author: Reese Kuper
Purpose: Run multiple benchmarks for memsys testing
test configurations specificied in configs.yml
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
import re
import json
from collections import Counter
from colorama import Fore, Back, Style
sys.path.insert(0, 'scripts')
from backends import *
from benchmarks import *
from experiments import *



"""
Parse the YAML configurations to make sure they make sense
"""
def parse_general_yml(configs):
    parse_errors = 0
    for general in configs["general"]:
        if general == "paths":
            configs["general"][general]["script-root"] = os.getcwd()
            if "redis-directory" in configs["general"][general]:
                configs["general"][general]["redis-directory"] = os.getcwd() + \
                    configs["general"][general]["redis-directory"]
            if general == "experiments":
                for experiment in configs["general"][general]:
                    if experiment not in configs["experiments"]:
                        print_error("Could not find experiment, " + experiment); parse_errors += 1
    return parse_errors

def parse_experiment_yml(configs):
    parse_errors = 0
    output_directories = []
    for experiment in configs["experiments"]:
        for setting in configs["experiments"][experiment]:
            if setting == "numa-node-configs":
                for node in configs["experiments"][experiment][setting]:
                    if int(configs["experiments"][experiment][setting][node]) > numa.info.get_max_node():
                        print_error(node + " value not in range of available NUMA nodes"); parse_errors += 1
            elif setting == "paths":
                output_directory = configs["experiments"][experiment][setting]["output-directory"]
                if output_directory in output_directories:
                    print_error("Found duplicate output directory, " + output_directory + ", in multiple experiments")
                    parse_errors += 1
                else:
                    output_directories.append(output_directory)
            elif setting == "benchmarks":
                for benchmark in configs["experiments"][experiment][setting]:
                    found_benchmark = False
                    for suite in configs["benchmarks"]:
                        for available_benchmark in configs["benchmarks"][suite]:
                            if available_benchmark == benchmark:
                                found_benchmark = True
                    if not found_benchmark:
                        print_error("Could not find benchmark, " + benchmark); parse_errors += 1
    return parse_errors

def parse_benchmark_yml(configs):
    parse_errors = 0
    for suite in configs["benchmarks"]:
        if suite == "overrides": continue
        for benchmark in configs["benchmarks"][suite]:
            if not (os.path.exists(configs["benchmarks"][suite][benchmark]["info"]["path"])):
                print_error("Path to benchmark " + benchmark + " could not be found"); parse_errors += 1
            executable = os.path.join(configs["benchmarks"][suite][benchmark]["info"]["path"], \
                            configs["benchmarks"][suite][benchmark]["info"]["executable"])
            if not (os.path.exists(executable)):
                print_error("Executable for benchmark " + benchmark + " could not be found"); parse_errors += 1
    return parse_errors



"""
Parse the yml configuration files (general, experiments, benchmarks)
"""
def parse_ymls(args, configs):
    config_filename = ""
    errors = 0
    for config in configs:
        if config == "general":
            errors = parse_general_yml(configs); config_filename = args.general
        elif config == "experiments":
            errors = parse_experiment_yml(configs); config_filename = args.experiments
        elif config == "benchmarks":
            errors = parse_benchmark_yml(configs); config_filename = args.benchmarks
        if errors > 0:
            print_error("Found " + str(errors) + " error(s) inside of " + config_filename)
    return errors



"""
Build the benchmark objects for easier use and extensability
Per benchmark:
    1. Create benchmark object from the corresponding benchmark suite for the current sub-benchmark
    2. Add info (executable, path, etc.) and the execution parameters to the object
    3. Append benchmark object list with that object
"""
def build_benchmarks(benchmark_configs, experiment_benchmarks):
    benchmark_suites = {}
    benchmarks_pathing = {}

    for benchmark_suite in benchmark_configs:

        # Skip overrides
        if benchmark_suite == "overrides" or not (benchmark_suite in experiment_benchmarks):
            continue

        benchmarks_pathing[benchmark_suite] = []
        benchmark_suites[benchmark_suite] = []

        # Begin building objects
        for benchmark in benchmark_configs[benchmark_suite]:

            # Step 1. Create needed benchmark type dynamically based on name
            if globals().get(benchmark_suite) is not None:
                benchmark_i = globals().get(benchmark_suite)(benchmark)
            else:
                print_warning("Defaulting benchmark suite" + str(benchmark_suite))
                benchmark_i = benchmark(benchmark)

            # Step 2: Add benchmark information and parameters to benchmark object
            for info in benchmark_configs[benchmark_suite][benchmark]["info"]:
                benchmark_i.add_info(info, benchmark_configs[benchmark_suite][benchmark]["info"][info])
            for parameter in benchmark_configs[benchmark_suite][benchmark]["parameters"]:
                if parameter in benchmark_configs["overrides"]:
                    benchmark_i.add_parameter(parameter, benchmark_configs["overrides"][parameter])
                else:
                    benchmark_i.add_parameter(parameter, benchmark_configs[benchmark_suite][benchmark]["parameters"][parameter])

            # Append benchmark to benchmark list
            benchmarks_pathing[benchmark_suite].append(benchmark)
            benchmark_suites[benchmark_suite].append(benchmark_i)
    return benchmark_suites, benchmarks_pathing



"""
Build the experiment objects for easier use and extensability
Per experiment:
    1. Create experiment object based on name
    2. Add its configurations from the yml file
    3. Add built benchmarks to experiment
    4. Append experiment to the list of experiments to return
"""
def build_experiments(configs):
    experiments = []
    errors = 0
    for experiment_name in configs["experiments"]:

        # Make sure experiment should be tested
        if experiment_name not in configs["general"]["experiments"]:
            continue

        # Step 1. Create needed benchmark type dynamically based on name
        if globals().get(experiment_name) is not None:
            experiment_i = globals().get(experiment_name)(experiment_name)
        else:
            print_error("Could not find experiment, " + experiment.name + ", in the experiments YAML file")
            return experiments, (errors+1)

        # Step 2a. Add experiment's result's output path first since it's needed later in step 2b
        if "paths" not in configs["experiments"][experiment_name]:
            experiment_i.output_directory = experiment_name
        else:
            experiment_i.output_directory = configs["experiments"][experiment_name]["paths"]["output-directory"]

        # Step 2b. Add experiment's configurations from the configuration yml file
        for config in configs["experiments"][experiment_name]:
            if config == "benchmarks":
                # Step 3.  Add built benchmarks to experiment
                benchmark_suites, benchmarks_pathing = build_benchmarks(configs["benchmarks"], \
                                                configs["experiments"][experiment_name]["benchmarks"])
                experiment_i.benchmark_suites = benchmark_suites
                experiment_i.benchmarks_pathing = benchmarks_pathing

                # Default active output file just in case an experiment forgot to make one
                # also add suite and benchmark dictionary result entries to the experiment for processing
                for benchmark_suite in benchmark_suites:
                    for benchmark in benchmark_suites[benchmark_suite]:
                        benchmark.active_output_file = os.path.join(experiment_i.output_directory,
                                benchmark.suite, benchmark.name, "raw", benchmark.name + "-0.txt")
                        if benchmark.suite not in experiment_i.results: experiment_i.results[benchmark.suite] = {}
                        experiment_i.results[benchmark.suite][benchmark.name] = {}
            elif config == "operations":
                experiment_i.operations = configs["experiments"][experiment_name][config]
            else:
                errors = experiment_i.init_config(config, configs["experiments"][experiment_name][config])
                if errors > 0:
                    print_error("Found error(s) in experiment, " + experiment.name + ", configurations")
                    return experiments, errors

        if "execute" in experiment_i.operations:
            experiment_i.create_result_directories()

        # Step 4. Append experiment to the list of experiments to return
        experiments.append(experiment_i)
    return experiments, errors




"""
Execute, process, and/or analyze each benchmark based on the set configs in the YAML file
"""
def operate_experiments(general_configs, experiments):
    for experiment in experiments:
        for operation in experiment.operations:
            if operation == "execute":
                experiment.execute_wrapper(general_configs)
            elif operation == "process":
                experiment.process_wrapper(general_configs)
            elif operation == "analyze":
                experiment.analyze(general_configs)
    return



"""
Main: Parses and adjusts arguments passed in to ensure it matches system configs. Also
      calls execute and process functions.
"""
def main():
    # Parse arguments, ensure they make sense
    parser = argparse.ArgumentParser()
    parser.add_argument("-g", "--general", help = \
            "General configuration YAML file (default = general.yml)", default="general.yml")
    parser.add_argument("-e", "--experiments", help = \
            "Experiments configuration YAML file (default = experiments.yml)", default="experiments.yml")
    parser.add_argument("-b", "--benchmarks", help = \
            "Benchmarks configuration YAML file (default = benchmarks.yml)", default="benchmarks.yml")
    parser.add_argument("-i", "--interactive", help = \
            "Interactive mode for confirming options and interacting with the analysis tool", action='store_true')
    args = parser.parse_args()

    # Open up the yaml files and get the configurations. Report any found errors
    config_filename = args.general
    config_types = ["general", "experiments", "benchmarks"]
    configs = {}
    try:
        for config in config_types:
            config_filename = args.general if (config == "general") else \
                            (args.experiments if (config == "experiments") else \
                            args.benchmarks)
            if not os.path.exists(os.path.join("configs", config_filename)):
                print_error(config + " YML file, " + config_filename + ", was not found!"); return
            yml = open(os.path.join("configs", config_filename), 'r')
            loaded_config = yaml.safe_load(yml)
            configs[config] = loaded_config
    except yaml.YAMLError as exception:
        print_error(exception); print_error(config_filename + " configuration file is not formatted correctly!"); return

    # Create the general directories if not found
    general_directories = ["results", "benchmarks", "tools", "scripts"]
    for general_directory in general_directories:
        if not os.path.exists(general_directory): os.mkdir(general_directory)

    # Ensure yaml files makes sense
    if parse_ymls(args, configs) != 0:
        return

    # Grab all of the benchmarks in a list
    # benchmarks = build_benchmark_objects(general, configs)
    experiments, errors = build_experiments(configs)
    if errors > 0: return

    # General function to execute, process, and analyze the experiments
    operate_experiments(configs["general"], experiments)
    return



if __name__=="__main__":
    main()
