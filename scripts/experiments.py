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
        errors = 0
        return errors


    # Recreate results directory if it does not exist
    def create_result_directories(self):
        relative_output_directory = os.path.join("results", self.output_directory)
        if os.path.exists(relative_output_directory):
            shutil.rmtree(relative_output_directory)
        os.mkdir(relative_output_directory)
        for benchmark in self.benchmarks_pathing:
            os.mkdir(os.path.join(relative_output_directory, benchmark))
            for sub_benchmark in self.benchmarks_pathing[benchmark]:
                os.mkdir(os.path.join(relative_output_directory, benchmark, sub_benchmark))
                os.mkdir(os.path.join(relative_output_directory, benchmark, sub_benchmark, "raw"))


    def change_pcm_output_csv_files(self, general_configs, name):
        general_path_name = os.path.join(general_configs["paths"]["script-root"], \
                                         general_configs["paths"]["results-directory"], name)
        for exe_prefix in general_configs["exe-prefixes"]:
            if "pcm" in exe_prefix:
                new_exe_pcm_prefix = general_configs["exe-prefixes"][exe_prefix].split(" ")
                for parameter_index in range(len(new_exe_pcm_prefix)):
                    if "csv" in new_exe_pcm_prefix[parameter_index]:
                        new_exe_pcm_prefix[parameter_index] = "-csv=" + general_path_name + "-" + exe_prefix + ".csv"
                general_configs["exe-prefixes"][exe_prefix] = " ".join(new_exe_pcm_prefix)


    # NOTE: Override to define how to run your experiment
    def execute(self, general_configs, benchmark):
        for sample in range(general_configs["script-settings"]["samples"]):
            output_name_order = [benchmark.name, str(sample) + ".txt"]
            benchmark.active_output_file = os.path.join(self.output_directory, benchmark.suite, \
                benchmark.name, "raw", "-".join(output_name_order))
            self.change_pcm_output_csv_files(general_configs, benchmark.active_output_file)
            benchmark.execute_wrapper(general_configs)


    def execute_wrapper(self, general_configs):
        # Save the exe-prefixes: overwritten later for paths and different numa nodes
        exe_prefixes_before = general_configs["exe-prefixes"].copy()
        for benchmark_suite in self.benchmark_suites:
            for benchmark in self.benchmark_suites[benchmark_suite]:
                self.execute(general_configs, benchmark)
        general_configs["exe-prefixes"] = exe_prefixes_before


    # NOTE: Override to define how to process your experiment
    def process(self, general_configs, complete_results, benchmark):
        benchmark.active_glob = os.path.join(general_configs["paths"]["results-directory"], \
            self.output_directory, benchmark.suite, benchmark.name, "raw", benchmark.name)
        complete_results[benchmark.suite][benchmark.name][mem_config] = benchmark.process_wrapper(general_configs)


    def process_wrapper(self, general_configs):
        complete_results = {}
        experiment_output_path = os.path.join(general_configs["paths"]["results-directory"], self.output_directory)
        for benchmark_suite in self.benchmark_suites:
            complete_results[benchmark_suite] = {}
            suite_output_path = os.path.join(experiment_output_path, self.benchmark_suites[benchmark_suite][0].suite)
            for benchmark in self.benchmark_suites[benchmark_suite]:
                complete_results[benchmark.suite][benchmark.name] = {}
                benchmark_output_path = os.path.join(suite_output_path, benchmark.name)
                self.process(general_configs, complete_results, benchmark)
                write_data(complete_results, os.path.join(benchmark_output_path, benchmark.name + ".json"))
            write_data(complete_results, os.path.join(suite_output_path, benchmark.suite + ".json"))
        write_data(complete_results, os.path.join(experiment_output_path, self.name + ".json"))
        self.results = complete_results


    def analyze(self):
        pass



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

            # Per benchmark, run 'sample' nmumber of the same benchmark to take an average of the results
            for sample in range(general_configs["script-settings"]["samples"]):
                output_name_order = "-".join([benchmark.name, mem_config, str(sample)])
                benchmark.active_output_file = os.path.join(self.output_directory, \
                    benchmark.suite, benchmark.name, "raw", output_name_order)
                self.change_pcm_output_csv_files(general_configs, benchmark.active_output_file)
                benchmark.execute_wrapper(general_configs)


    def process(self, general_configs, complete_results, benchmark):
        for mem_config in self.mem_configs:
            output_name_order = [benchmark.name, mem_config]
            benchmark.active_glob = os.path.join(general_configs["paths"]["results-directory"], \
                self.output_directory, benchmark.suite, benchmark.name, "raw", "-".join(output_name_order))
            complete_results[benchmark.suite][benchmark.name][mem_config] = benchmark.process_wrapper(general_configs)
