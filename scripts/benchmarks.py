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
import re
import json
from collections import Counter
from colorama import Fore, Back, Style
from backends import *



"""""""""""""""""""""""""""""""""""""""

Base benchmark (suite) class(es)

"""""""""""""""""""""""""""""""""""""""
class benchmark:
    vmstat_metrics = ["numa_hit", "numa_miss", "numa_page_migrated", "pgmigrate_success", \
            "pgmigrate_fail", "numa_local", "numa_foreign"]
    def __init__(self, name="Null", suite="Null"):
        self.name = name
        self.suite = suite if suite != "Null" else self.name
        self.parameters = []
        self.info = {}
        self.results = {}

    def add_info(self, name, value):
        self.info[name] = str(value)


    # NOTE: Overwrite this if need be!
    def add_parameter(self, name, value):
        self.parameters.append("--" + name + "=" + str(value))


    def add_result(self, name, value, specificity):
        benchmark.results[self.suite][self.name][specificity][name] = value


    def get_vmstat_info(self, difference=False, starting_values={}):
        vmstat_values = {}
        with open("/proc/vmstat", 'r') as vmstat:
            for line in vmstat:
                for metric in benchmark.vmstat_metrics:
                    if metric in line:
                        if difference:
                            vmstat_values[metric] = int(line.strip().split()[1]) - starting_values[metric]
                        else:
                            vmstat_values[metric] = int(line.strip().split()[1])
        return vmstat_values


    def change_pcm_output_csv_files(self, general_configs, name):
        root_to_glob = os.path.join(general_configs["paths"]["script-root"], general_configs["paths"]["results-directory"], name)
        for exe_prefix in general_configs["exe-prefixes"]:
            if "pcm" in exe_prefix:
                new_exe_pcm_prefix = general_configs["exe-prefixes"][exe_prefix].split(" ")
                for parameter_index in range(len(new_exe_pcm_prefix)):
                    if "csv" in new_exe_pcm_prefix[parameter_index]:
                        new_exe_pcm_prefix[parameter_index] = "-csv=" + root_to_glob + "-" + exe_prefix + ".csv"
                general_configs["exe-prefixes"][exe_prefix] = " ".join(new_exe_pcm_prefix)


    def execute(self, general_configs, sample, start_str_order=[]):
        if len(start_str_order) == 0:
            start_str_order=["Suite=" + self.suite, "Benchmark=" + self.name, \
                    "Sample=" + str(sample), "\nCommand: " + self.active_cmd]
        print(); print_step("EXECUTE - START", Fore.GREEN, " ".join(start_str_order))
        if not os.path.exists(self.info["path"]):
            print_error("Could not find path to benchmark's executable"); return

        # Set up timer, outputs, and starting data before running
        output_file = os.path.join(general_configs["paths"]["results-directory"], self.active_name + ".txt")
        output_fp = open(output_file, 'w')
        starting_numa_results = self.get_vmstat_info()
        start_time = time.time()

        # RUN!
        try:
            update = time_counter = 0
            active_benchmark = subprocess.Popen(self.active_cmd, cwd=self.info["path"], \
                stdout=output_fp, shell=True, stderr=subprocess.DEVNULL)
            while active_benchmark.poll() is None:
                time.sleep(1)
                time_counter += 1
                if time_counter >= general_configs["script-settings"]["status-update-interval"]:
                    time_counter = 0
                    update += 1
                    print_step("UPDATE - " + str(update), Fore.YELLOW, self.suite + " - " + self.name + \
                        ": " + datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
        except:
            print_error("Failed to run benchmark!")
            try:
                active_benchmark.terminate()
            except:
                pass

        # End and capture data results
        end_time = time.time()
        final_numa_results = self.get_vmstat_info(True, starting_numa_results)
        for parameter in final_numa_results:
            output_fp.write(parameter + " = " + str(final_numa_results[parameter]) + "\n")
        output_fp.close()
        print_step("EXECUTE - FINISH", Fore.GREEN, "Time taken (nearest second): " + str(end_time - start_time) + "s")


    # NOTE: Overwrite this if needed for each added benchmark suite!
    def execute_wrapper(self, general_configs):
        for sample in range(general_configs["script-settings"]["samples"]):
            # Set active name, PCM file outputs, and command, then run!
            self.active_name = self.active_glob + "-" + str(sample)
            self.change_pcm_output_csv_files(general_configs, self.active_name)
            cmd_order = [" ".join(general_configs["exe-prefixes"].values()), \
                        "./" + self.info["executable"], \
                        " ".join(self.parameters)]
            self.active_cmd = " ".join(cmd_order)
            self.execute(general_configs, sample)


    def process_pcm(self, general_configs, sample, data):
        process_errors = 0
        pcm_files = []
        for exe_prefix in general_configs["exe-prefixes"]:
            if "pcm" in exe_prefix and "csv" in general_configs["exe-prefixes"][exe_prefix]:
                pcm_files.append(self.active_glob + "-" + str(sample) + "-" + exe_prefix + ".csv")
        try:
            for pcm_file in pcm_files:
                if not os.path.exists(pcm_file):
                    print_error("PCM CSV file, " + pcm_file + ", was not found to parse"); process_errors += 1; break
                with open(pcm_file, mode='r') as file:
                    lines = []
                    for line in file:
                        lines.append(line.strip().split(","))

                    for line_number in range(len(lines)):
                        for item_number in range(len(lines[line_number])):
                            category = lines[0][item_number]
                            sub_category = lines[1][item_number]
                            try:
                                value = float(lines[2][item_number].strip())
                            except:
                                continue

                            if line_number == 0:
                                if "System" in category:
                                    if category == "System":
                                        data["System"][sub_category] = value
                                    else:
                                        data["System"][category[len("System "):]] = {}
                                        data["System"][category[len("System "):]][sub_category] = value

                                elif "Socket" in category:
                                    if category.replace("Socket ", "").isdigit():
                                        data["System"]["Sockets"][category][sub_category] = value
                                    elif category.split(" (Socket ")[-1][:len(category.split(" (Socket ")[1])-1].isdigit():
                                        category_socket = category.split(" (Socket ")[-1][:len(category.split(" (Socket ")[1])-1]
                                        category_nonsocket = category.split(" (Socket ")[0]
                                        if category_nonsocket not in data["System"]["Sockets"]["Socket " + category_socket]["Cores"]:
                                            data["System"]["Sockets"]["Socket " + category_socket]["Cores"][category_nonsocket] = {}
                                        data["System"]["Sockets"]["Socket " + category_socket][\
                                            "Cores"][category_nonsocket][sub_category] = value

                                elif "SKT" in category:
                                    cat_split_nums = re.sub('(\d+(\.\d+)?)', r' \1 ', category).strip().split(" ")
                                    socket = "Socket " + cat_split_nums[1]
                                    if len(cat_split_nums) > 2:
                                        data["System"]["Sockets"][socket][" ".join(cat_split_nums[2:])] = {}
                                        data["System"]["Sockets"][socket][" ".join(cat_split_nums[2:])][sub_category] = value
                                    else:
                                        sub_cat_split_nums = re.sub('(\d+(\.\d+)?)', r' \1 ', sub_category).split(" ")
                                        sub_cat_area = "Channels" if sub_cat_split_nums[0] == "Ch" else \
                                                            ("iMCs" if sub_cat_split_nums[0] == "iMC" else "Ignore")
                                        sub_cat_num = ("Channel " + sub_cat_split_nums[1]) if sub_cat_split_nums[0] == "Ch" \
                                                        else ("iMC " + sub_cat_split_nums[1])

                                        if sub_cat_area != "Ignore":
                                            if len(sub_cat_split_nums) > 1 and sub_cat_split_nums[1].isdigit() and \
                                                    sub_cat_num not in data["System"]["Sockets"][socket][sub_cat_area]:
                                                data["System"]["Sockets"][socket][sub_cat_area][sub_cat_num] = {}
                                            data["System"]["Sockets"][socket][sub_cat_area][sub_cat_num][\
                                                " ".join(sub_cat_split_nums[2:]).strip()] = value
                                        else:
                                            data["System"]["Sockets"][socket][sub_category] = value

                            elif line_number == 1:
                                if "SKT" in sub_category and sub_category.replace("SKT", "").isdigit():
                                    data["System"]["Sockets"]["Socket " + sub_category.replace("SKT", "")][category] = value
        except:
            print_error("Error when processing PCM file"); process_errors += 1
        return process_errors


    def process_vmstat(self, general_configs, sample, data):
        with open(self.active_glob + "-" + str(sample) + ".txt", "r") as fp:
            for line in fp:
                for vmstat_metric in benchmark.vmstat_metrics:
                    if vmstat_metric in line:
                        data["System"][vmstat_metric.replace('_', '-')] = float(line.split(" ")[2].strip())



    # NOTE: Overwrite this for each added benchmark suite!
    def process_specific(self, general_configs, sample, data):
        print_warning("This benchmark has no specific benchmark results!")


    def process_all_monitors(self, general_configs, sample, data):
        self.process_pcm(general_configs, sample, data["general"])
        self.process_vmstat(general_configs, sample, data["general"])
        self.process_specific(general_configs, sample, data["specific"])



    def process(self, general_configs, processed_data, sample, process_str_order=[]):
        if len(process_str_order) == 0:
            process_str_order=["Suite=" + self.suite, "Benchmark=" + self.name, "Sample=" + str(sample)]
        print_step("PROCESS", Fore.MAGENTA, " ".join(process_str_order) + " : Processing all data")
        data = {}
        data["specific"] = {}
        data["general"] = {}
        data["general"]["System"] = {}
        data["general"]["System"]["Sockets"] = {}
        num_sockets = int(subprocess.check_output('cat /proc/cpuinfo | grep "physical id" | sort -u | wc -l', shell=True))
        for socket in range(num_sockets):
            data["general"]["System"]["Sockets"]["Socket " + str(socket)] = {}
            data["general"]["System"]["Sockets"]["Socket " + str(socket)]["Cores"] = {}
            data["general"]["System"]["Sockets"]["Socket " + str(socket)]["Channels"] = {}
            data["general"]["System"]["Sockets"]["Socket " + str(socket)]["iMCs"] = {}
        self.process_all_monitors(general_configs, sample, data)
        sampled_file = open(self.active_glob + "-" + str(sample) + ".json", "w")
        json.dump(data, sampled_file, indent=4)
        sampled_file.close()
        processed_data[str(sample)] = data


    # NOTE: Overwrite this if needed for each added benchmark suite!
    def process_wrapper(self, general_configs):
        processed_data = {}
        for sample in range(general_configs["script-settings"]["samples"]):
            self.process(general_configs, processed_data, sample)

        # Flatten the data processed from each sample
        processed_data = average_dicts(processed_data)
        return processed_data







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

    def execute_wrapper(self, general_configs):
        for sample in range(general_configs["script-settings"]["samples"]):
            if manage_redis(general_configs, "start") > 0:
                print_error("Could not start redis-server"); return

            # Set active name, PCM file outputs, and command, then run!
            self.active_name = self.active_glob + "-" + str(sample)
            self.change_pcm_output_csv_files(general_configs, self.active_name)
            cmd_order = [" ".join(general_configs["exe-prefixes"].values()), \
                        "./" + self.info["executable"], \
                        " ".join(self.parameters)]
            self.active_cmd = " ".join(cmd_order)
            self.execute(general_configs, sample)

            if manage_redis(general_configs, "end") > 0:
                print_error("Could not kill redis-server"); return


class memtier(benchmark):
    def __init__(self, name="Null"):
        super().__init__(name, "memtier")
        self.name = name

    def add_parameter(self, name, value):
        if str(value) == "true": self.parameters.append("--" + name)
        else: self.parameters.append("--" + name + "=" + str(value))

    def execute_wrapper(self, general_configs):
        for sample in range(general_configs["script-settings"]["samples"]):
            if manage_redis(general_configs, "start") > 0:
                print_error("Could not start redis-server"); return

            # Set active name, PCM file outputs, and command, then run!
            self.active_name = self.active_glob + "-" + str(sample)
            self.change_pcm_output_csv_files(general_configs, self.active_name)
            cmd_order = [" ".join(general_configs["exe-prefixes"].values()), \
                        "./" + self.info["executable"], \
                        " ".join(self.parameters)]
            self.active_cmd = " ".join(cmd_order)
            self.execute(general_configs, sample)

            if manage_redis(general_configs, "end") > 0:
                print_error("Could not kill redis-server"); return


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

    def process_specific(self, general_configs, sample, data):
        print_warning("This benchmark has no specific benchmark results!")


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

