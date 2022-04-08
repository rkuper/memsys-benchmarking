"""""""""""""""""""""""""""""""""""""""""""""""""""
Define experiments to run
===================================================
Filename: experiments.py
Author: Reese Kuper
Purpose: Create experiments through adding off of
the generic experiment class
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
        self.benchmarks = []
        self.benchmarks_pathing = {}
        self.results = {}
        self.output_directory = "Null"
        self.operations = {"execute" : False, "process" : False, "analyze" : False}
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
        if not os.path.exists(relative_output_directory):
            os.mkdir(relative_output_directory)
            for benchmark in self.benchmarks_pathing:
                os.mkdir(os.path.join(relative_output_directory, benchmark))
                for sub_benchmark in self.benchmarks_pathing[benchmark]:
                    os.mkdir(os.path.join(relative_output_directory, benchmark, sub_benchmark))
        else:
            for benchmark in self.benchmarks_pathing:
                if not os.path.exists(os.path.join(relative_output_directory,benchmark)):
                    os.mkdir(os.path.join(relative_output_directory, benchmark))
                    for sub_benchmark in self.benchmarks_pathing[benchmark]:
                        os.mkdir(os.path.join(relative_output_directory, benchmark, sub_benchmark))
                else:
                    for sub_benchmark in self.benchmarks_pathing[benchmark]:
                        if not os.path.exists(os.path.join(relative_output_directory, benchmark, sub_benchmark)):
                            os.mkdir(os.path.join(relative_output_directory, benchmark, sub_benchmark))
        pass

    # NOTE: Override to define how to run your experiment
    def execute(self, general_configs):
        for benchmark in self.benchmarks:
            for sample in range(general_configs["execution"]["samples"]):

                # Set up execution prefixes based on default values in general configs (can be overriden)
                exe_prefixes = ""
                for exe_prefix in general_configs["exe-prefixes"]:
                    if exe_prefix == "numa":
                        cpu_node = str(general_configs["execution"]["cpu-numa-node"])
                        mem_node = str(general_configs["execution"]["mem-numa-node"])
                        exe_prefixes += " " + general_configs["exe-prefixes"][exe_prefix].replace("{1}", cpu_node).replace("{2}", mem_node)
                    else:
                        exe_prefixes += " " + general_configs["exe-prefixes"][exe_prefix]
                exe_prefixes = exe_prefixes.strip()

                output_filename = benchmark.name + "_" + str(sample) + ".txt"
                benchmark.execute(general_configs, exe_prefixes, output_filename)
        pass

    def process(self):
        pass

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

    def execute(self, general_configs):
        for benchmark in self.benchmarks:
            for mem_config in self.mem_configs:

                # Set up execution prefixes based on default values in general configs (can be overriden)
                exe_prefixes = ""
                for exe_prefix in general_configs["exe-prefixes"]:
                    if exe_prefix == "numa":
                        if mem_config == "local":
                            cpu_node = str(self.big_cpu_node)
                            mem_node = str(self.big_mem_node)
                        elif mem_config == "remote":
                            cpu_node = str(self.small_cpu_node)
                            mem_node = str(self.big_mem_node)
                        else:
                            cpu_node = str(self.small_cpu_node)
                            mem_node = str(self.small_mem_node) + "," + str(self.big_mem_node)

                        exe_prefixes += " " + general_configs["exe-prefixes"][exe_prefix].replace("{1}", cpu_node).replace("{2}", mem_node)
                    else:
                        exe_prefixes += " " + general_configs["exe-prefixes"][exe_prefix]
                exe_prefixes = exe_prefixes.strip()

                for sample in range(general_configs["execution"]["samples"]):
                    output_name_order = [benchmark.name, mem_config, str(sample), ".txt"]
                    benchmark.execute(general_configs, exe_prefixes, self.output_directory, "_".join(output_name_order))
        pass
