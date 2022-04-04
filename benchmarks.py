"""""""""""""""""""""""""""""""""""""""""""""""""""
Run benchmark suites for testing memory system
===================================================
Filename: benchmarks.py
Author: Reese Kuper
Purpose: Classes for benchmarks
"""""""""""""""""""""""""""""""""""""""""""""""""""

import os
import signal
import sys
import time
import argparse
import yaml
import numa
import backends



"""""""""""""""""""""""""""""""""""""""

Base benchmark (suite) class(es)

"""""""""""""""""""""""""""""""""""""""
class benchmark:
    benchmark_status = {}
    results = {}

    def __init__(self, name="Null", suite="Null"):
        self.name = name
        self.suite = suite
        self.parameters = []
        self.info = {}
        corrected_suite = self.suite if self.suite != "Null" else self.name
        if name != "Null":
            if corrected_suite not in benchmark.benchmark_status or corrected_suite not in benchmark.results:
                benchmark.benchmark_status[corrected_suite] = {}
                benchmark.results[corrected_suite] = {}
            benchmark.benchmark_status[corrected_suite][self.name] = "Queued"
            benchmark.results[corrected_suite][self.name] = {}
            benchmark.results[corrected_suite][self.name]["general"] = {}
            benchmark.results[corrected_suite][self.name]["specific"] = {}

    def add_info(self, name, value):
        self.info[name] = str(value)

    # NOTE: Overwrite this if need be!
    def add_parameter(self, name, value):
        self.parameters.append("--" + name + "=" + str(value))

    def add_result(self, name, value, specificity):
        if self.suite != "Null":
            benchmark.results[self.suite][self.name][specificity][name] = value
        else:
            benchmark.results[self.name][specificity][name] = value

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

    # NOTE: Overwrite this if needed for each added benchmark suite!
    def execute_specific(self, general, cmd):


        print("[EXECUTE] Running " + self.name + "...", end=" ")
        starting_numa_results = self.get_vmstat_info()
        # os.system(full_cmd)
        true_numa_results = self.get_vmstat_info(True, starting_numa_results)
        print("Done!")




    def execute(self, general):
        cmd = ""
        for exe_prefix in general["exe-prefixes"]:
            cmd += general["exe-prefixes"][exe_prefix]
        cmd += "./" + self.info["executable"]
        for parameter in self.parameters:
            cmd += " " + parameter

        if not os.path.exists(self.info["path"]):
            print("[ERROR] Could not find path to benchmark's executable")
            return
        os.system("cd " + self.info["path"])
        self.execute_specific(general, cmd)
        os.system("cd " + general["paths"]["script-root"])

    def process_pcm(self, general):
        print("[", end="")
        if self.suite != "Null":
            print(self.suite + " - ", end="")
        print(self.name + "]i Processing pcm results...", end=" ")

        print("Done!")

    def process_vmstat(self, general):
        print("[", end="")
        if self.suite != "Null":
            print(self.suite + " - ", end="")
        print(self.name + "] Processing vmstat/NUMA results...", end=" ")

        print("Done!")

    # NOTE: Overwrite this for each added benchmark suite!
    def process_specific(self, general):
        print("[Warning] This benchmark has no specific benchmark results!")

    def process(self, general):
        self.process_pcm(general)
        self.process_vmstat(general)
        self.process_specific(general)



"""""""""""""""""""""""""""""""""""""""""""""""""""""""""

Add new benchmarks by creating new classes below!

"""""""""""""""""""""""""""""""""""""""""""""""""""""""""
class tailbench(benchmark):
    def __init__(self, name="Null"):
        super().__init__(name, "tailbench")
        self.name = name

    def add_parameter(self, name, value):
        self.parameters.append("TBENCH_" + name.upper() + "=" + str(value))

    # def execute_specific(self, general, cmd):
    #     return

    # def process_specific(self, general):
    #     return


class ycsb(benchmark):
    def __init__(self, name="Null"):
        super().__init__(name, "ycsb")
        self.name = name

    def add_parameter(self, name, value):
        self.parameters.append("-p " + name + "=" + str(value))

    # def execute_specific(self, general):
    #     return

    # def process_specific(self, general):
    #     return


class memtier(benchmark):
    def __init__(self, name="Null"):
        super().__init__(name, "memtier")
        self.name = name


class pmbench(benchmark):
    def __init__(self, name="Null"):
        super().__init__(name, "pmbench")
        self.name = name


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

