"""""""""""""""""""""""""""""""""""""""""""""""""""
Define benchmarks to test
===================================================
Filename: benchmarks.py
Author: Reese Kuper
Purpose: Create benchmarks through adding of the
generic benchmark class
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



"""""""""""""""""""""""""""""""""""""""

Base benchmark (suite) class(es)

"""""""""""""""""""""""""""""""""""""""
class benchmark:
    benchmark_statuses = {}
    results = {}

    def __init__(self, name="Null", suite="Null"):
        self.name = name
        self.suite = suite
        self.parameters = []
        self.info = {}
        corrected_suite = self.suite if self.suite != "Null" else self.name
        if name != "Null":
            if corrected_suite not in benchmark.benchmark_statuses or corrected_suite not in benchmark.results:
                benchmark.benchmark_statuses[corrected_suite] = {}
                benchmark.results[corrected_suite] = {}
            benchmark.benchmark_statuses[corrected_suite][self.name] = "Queued"
            benchmark.results[corrected_suite][self.name] = {}
            benchmark.results[corrected_suite][self.name]["general"] = {}
            benchmark.results[corrected_suite][self.name]["specific"] = {}

    def add_info(self, name, value):
        self.info[name] = str(value)


    # NOTE: Overwrite this if need be!
    def add_parameter(self, name, value):
        self.parameters.append("--" + name + "=" + str(value))


    def add_result(self, name, value, specificity):
        benchmark.results[self.suite][self.name][specificity][name] = value


    def get_vmstat_info(self, difference=False, starting_values={}):
        vmstat_metrics = ["numa_hit", "numa_miss", "numa_page_migrated", "pgmigrate_success", \
            "pgmigrate_fail", "numa_local", "numa_foreign"]
        vmstat_values = {}
        with open("/proc/vmstat", 'r') as vmstat:
            for line in vmstat:
                for metric in vmstat_metrics:
                    if metric in line:
                        if difference:
                            vmstat_values[metric] = int(line.strip().split()[1]) - starting_values[metric]
                        else:
                            vmstat_values[metric] = int(line.strip().split()[1])
        return vmstat_values


    def execute(self, general_configs, exe_prefixes, output_directory, output_filename):
        cmd = exe_prefixes + " ./" + self.info["executable"]
        cmd += " " + " ".join(self.parameters)
        if not os.path.exists(self.info["path"]):
            print_error("Could not find path to benchmark's executable"); return

        print_step("EXECUTE", Fore.GREEN, "Suite=" + self.suite + " Benchmark=" + self.name)
        print_step("EXECUTE", Fore.GREEN, "Running command: " + cmd)
        starting_numa_results = self.get_vmstat_info()
        start_time = time.time()

        output_location = os.path.join(general_configs["paths"]["results-directory"], output_directory, self.suite, self.name, output_filename)
        output_fp = open(output_location, 'w')
        try:
            update = 0
            active_benchmark = subprocess.Popen(cmd, cwd=self.info["path"], stdout=output_fp, shell=True, stderr=subprocess.DEVNULL)
            while active_benchmark.poll() is None:
                time.sleep(general_configs["script-settings"]["status-update-interval"])
                update += 1
                print(Fore.YELLOW + "[Update " + str(update) + "] " + Style.RESET_ALL + self.suite + " - " + self.name + ": " + \
                    datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
        except:
            print(Fore.RED + "[ERROR]" + Style.RESET_ALL + " Failed to run benchmark!")
            active_benchmark.terminate()

        end_time = time.time()
        final_numa_results = self.get_vmstat_info(True, starting_numa_results)
        print_step("EXECUTE", Fore.GREEN, "Finished! Took around " + str(end_time - start_time) + "s")


    # NOTE: Overwrite this if needed for each added benchmark suite!
    def execute_wrapper(self, general_configs, output_filename):
        pre_execute(general_configs)
        execute(general_configs, output_filename)
        post_execute(general_configs)


    def process_pcm(self, general_configs):
        print("[", end="")
        if self.suite != "Null":
            print(self.suite + " - ", end="")
        print(self.name + "] Processing pcm results...", end=" ")

        print("Done!")


    def process_vmstat(self, general_configs):
        print("[", end="")
        if self.suite != "Null":
            print(self.suite + " - ", end="")
        print(self.name + "] Processing vmstat/NUMA results...", end=" ")

        print("Done!")


    # NOTE: Overwrite this for each added benchmark suite!
    def process_specific(self, general_configs):
        print_warning("This benchmark has no specific benchmark results!")


    def process(self, general_configs):
        self.process_pcm(general_configs)
        self.process_vmstat(general_configs)
        self.process_specific(general_configs)


    # NOTE: Overwrite this if needed for each added benchmark suite!
    def process_wrapper(self, general_configs):
        self.process(general_configs)



"""""""""""""""""""""""""""""""""""""""""""""""""""""""""

Add new benchmarks by creating new classes below!

"""""""""""""""""""""""""""""""""""""""""""""""""""""""""
class tailbench(benchmark):
    def __init__(self, name="Null"):
        super().__init__(name, "tailbench")
        self.name = name

    def add_parameter(self, name, value):
        self.parameters.append("TBENCH_" + name.upper() + "=" + str(value))



class ycsb(benchmark):
    def __init__(self, name="Null"):
        super().__init__(name, "ycsb")
        self.name = name

    def add_parameter(self, name, value):
        self.parameters.append("-p " + name + "=" + str(value))

    # def execute_wrapper(self, general_configs, output_file, ...):
    #     manage_redis(cpu_node, mem_node, script_root, current_directory, action)
    #     manage_redis(general_configs["numa-config"]..., "start")
    #     self.execute(general_configs, output_file)
    #     manage_redis(general_configs["numa-config"]..., "end")




class memtier(benchmark):
    def __init__(self, name="Null"):
        super().__init__(name, "memtier")
        self.name = name



class pmbench(benchmark):
    def __init__(self, name="Null"):
        super().__init__(name, "pmbench")
        self.name = name

    def add_parameter(self, name, value):
        if name == "threads":
            self.parameters.append("--jobs=" + str(value))
        elif name == "time":
            self.parameters.append(str(value))
        else:
            self.parameters.append("--" + name + "=" + str(value))



class cachebench(benchmark):
    def __init__(self, name="Null"):
        super().__init__(name, "cachebench")
        self.name = name



class gapbs(benchmark):
    def __init__(self, name="Null"):
        super().__init__(name, "gapbs")
        self.name = name

    def add_parameter(self, name, value):
        self.parameters.append("--" + name + " " + str(value))

