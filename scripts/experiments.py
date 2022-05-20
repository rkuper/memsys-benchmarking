"""""""""""""""""""""""""""""""""""""""""""""""""""
Define experiments to run
===================================================
Filename: experiments.py
Author: Reese Kuper
Purpose: Create experiments through adding off of
the generic experiment class
"""""""""""""""""""""""""""""""""""""""""""""""""""

import os
import shutil
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
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from collections import Counter
from colorama import Fore, Back, Style
from backends import *
from benchmarks import *



"""""""""""""""""""""""""""""""""""""""

Base benchmark (suite) class(es)

"""""""""""""""""""""""""""""""""""""""
class experiment():
    experiment_statuses = {}
    overall_results = {}
    def __init__(self, name="Null"):
        self.name = name
        self.benchmark_suites = {}
        self.benchmarks_pathing = {}
        self.results = {}
        self.output_directory = "Null"
        self.operations = []
        experiment.overall_results[name] = {}
        if name != "Null" and (not (name in experiment.experiment_statuses)):
            experiment.experiment_statuses[name] = "Queued"


    # NOTE: Override per experiment to add custom configs to change up execute() with
    def init_config(self, config_name, config):
        return 0


    # Recreate results directory if it does not exist
    def create_output_directories(self, general_configs, operation, retain_old=False):
        if operation == "process": return
        top_directory = "results-directory" if operation == "execute" else "analysis-directory"
        relative_output_directory = os.path.join( \
                general_configs["paths"][top_directory], \
                self.output_directory)
        if not os.path.exists(relative_output_directory): os.mkdir(relative_output_directory)
        for benchmark_suite in self.benchmarks_pathing:
            if self.benchmarks_pathing[benchmark_suite] == []: continue
            relative_suite_directory = os.path.join(relative_output_directory, benchmark_suite)
            if not os.path.exists(relative_suite_directory): os.mkdir(relative_suite_directory)
            for benchmark in self.benchmarks_pathing[benchmark_suite]:
                relative_benchmark_directory = os.path.join(relative_suite_directory, benchmark)
                if os.path.exists(relative_benchmark_directory):
                    if not retain_old and operation != "analyze":
                        shutil.rmtree(relative_benchmark_directory)
                else:
                    os.mkdir(relative_benchmark_directory)
                    if operation != "analyze":
                        os.mkdir(os.path.join(relative_benchmark_directory, "raw"))


    # NOTE: Override to define how to run your experiment
    def execute(self, general_configs, benchmark):
        benchmark.active_glob = os.path.join(general_configs["paths"]["results-directory"], \
            self.output_directory, benchmark.suite, benchmark.name, "raw", benchmark.name)
        benchmark.execute_wrapper(general_configs)


    def execute_wrapper(self, general_configs):
        # Save the exe-prefixes: overwritten later for paths and different numa nodes
        exe_prefixes_before = general_configs["exe-prefixes"].copy()
        for benchmark_suite in self.benchmark_suites:
            if self.benchmark_suites[benchmark_suite] == []: continue
            for benchmark in self.benchmark_suites[benchmark_suite]:
                self.execute(general_configs, benchmark)
        general_configs["exe-prefixes"] = exe_prefixes_before


    # NOTE: Override to define how to process your experiment
    def process(self, general_configs, complete_results, benchmark):
        benchmark.active_glob = os.path.join(general_configs["paths"]["results-directory"], \
            self.output_directory, benchmark.suite, benchmark.name, "raw", benchmark.name)
        complete_results[benchmark.suite][benchmark.name][mem_config] = \
                benchmark.process_wrapper(general_configs)


    def process_wrapper(self, general_configs):
        complete_results = {}
        experiment_output_path = os.path.join(\
                general_configs["paths"]["results-directory"], \
                self.output_directory)
        for benchmark_suite in self.benchmark_suites:
            if self.benchmark_suites[benchmark_suite] == []: continue
            complete_results[benchmark_suite] = {}
            suite_output_path = os.path.join(experiment_output_path, \
                    self.benchmark_suites[benchmark_suite][0].suite)
            for benchmark in self.benchmark_suites[benchmark_suite]:
                complete_results[benchmark.suite][benchmark.name] = {}
                benchmark_output_path = os.path.join(suite_output_path, benchmark.name)
                self.process(general_configs, complete_results, benchmark)
                # write_data(complete_results, os.path.join(benchmark_output_path, benchmark.name + ".json"))
            write_data(complete_results, os.path.join(suite_output_path, benchmark.suite + ".json"))
        write_data(complete_results, os.path.join(experiment_output_path, self.name + ".json"))
        self.results = complete_results


    def analyze(self, general_configs, benchmark):
        benchmark.active_glob = os.path.join(general_configs["paths"]["analysis-directory"], \
            self.output_directory, benchmark.suite, benchmark.name, benchmark.name)
        pass


    def analyze_wrapper(self, general_configs):
        if self.results == {}:
            print_warning("Results not actively loaded, attempting to restore from .json file")
            results_path = os.path.join(general_configs["results-directory"], \
                                        self.name, self.name + ".json")
            if not os.path.exists(self.name + ".json"):
                print_error("Could not find " + self.name + ".json"); return
            self.results = json.load(results_path)

        for benchmark_suite in self.benchmark_suites:
            if self.benchmark_suites[benchmark_suite] == []: continue
            for benchmark in self.benchmark_suites[benchmark_suite]:
                self.analyze(general_configs, benchmark)



"""""""""""""""""""""""""""""""""""""""""""""""""""""""""

Add new benchmarks by creating new classes below!

"""""""""""""""""""""""""""""""""""""""""""""""""""""""""
class numa_mode_compare(experiment):
    def __init__(self, name="Null"):
        super().__init__(name)
        pass

    def init_config(self, config_name, config):
        errors = 0
        if config_name == "numa-node-configs":
            self.small_cpu_node = config["small-cpu-node"]
            if config["small-cpu-node"] > numa.info.get_max_node():
                print_error("small-cpu-node not in range of available NUMA nodes"); errors += 1
            self.small_mem_node = config["small-mem-node"]
            if config["small-cpu-node"] > numa.info.get_max_node():
                print_error("small-mem-node not in range of available NUMA nodes"); errors += 1
            self.big_cpu_node = config["big-cpu-node"]
            if config["small-cpu-node"] > numa.info.get_max_node():
                print_error("big-cpu-node not in range of available NUMA nodes"); errors += 1
            self.big_mem_node = config["big-mem-node"]
            if config["small-cpu-node"] > numa.info.get_max_node():
                print_error("big-mem-node not in range of available NUMA nodes"); errors += 1
        elif config_name == "numa-mem-configs":
            self.mem_configs = config
        return errors


    def execute(self, general_configs, benchmark):
        for mem_config in self.mem_configs:

            # Set up execution prefixes based on default values in general configs (can be overriden)
            if "numa" in general_configs["exe-prefixes"]:
                if mem_config == "local":
                    cpu_node = str(self.big_cpu_node)
                    mem_node = str(self.big_mem_node)
                elif mem_config == "remote":
                    cpu_node = str(self.small_cpu_node)
                    mem_node = str(self.big_mem_node)
                else:
                    cpu_node = str(self.small_cpu_node)
                    mem_node = str(self.small_mem_node) + "," + str(self.big_mem_node)
            general_configs["exe-prefixes"]["numa"] = "sudo numactl --cpunodebind=" + str(cpu_node) + \
                    " --membind=" + str(mem_node)

            output_glob_order = "-".join([mem_config, benchmark.name])
            benchmark.active_glob = os.path.join(self.output_directory, \
                    benchmark.suite, benchmark.name, "raw", output_glob_order)
            benchmark.execute_wrapper(general_configs)


    def process(self, general_configs, complete_results, benchmark):
        for mem_config in self.mem_configs:
            output_glob_order = [mem_config, benchmark.name]
            benchmark.active_glob = os.path.join(general_configs["paths"]["results-directory"], \
                    self.output_directory, benchmark.suite, benchmark.name, "raw", "-".join(output_glob_order))
            complete_results[benchmark.suite][benchmark.name][mem_config] = \
                    benchmark.process_wrapper(general_configs)


    def analyze(self, general_configs, benchmark):
        x_categories = {}
        for mem_config in self.mem_configs:
            x_categories[mem_config] = []
            # TODO: Collect data (historgram, etc.) per mem_config, then plot into separate graphs
            # Basically copy what I had had from the spreadsheet
            benchmark.active_glob = os.path.join(general_configs["paths"]["analysis-directory"], \
                    self.output_directory, benchmark.suite, benchmark.name, benchmark.name + "-" + mem_config)

            x_categories[config].append(self.results[benchmark.suite][benchmark.name][mem_config]["general"]\
                    ["general"]["System"]["Pack C-States"]["LLCRDMISSLAT (ns)"])




        pass
