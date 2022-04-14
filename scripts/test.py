import os
import signal
import sys
import time
import datetime
import argparse
import yaml
import numa
import subprocess

"""""""""""""""""""""""""""""""""""""""

Base benchmark (suite) class(es)

"""""""""""""""""""""""""""""""""""""""
class benchmark:
    benchmark_status = {}
    results = {}

    def __init__(self, name="Null", suite="Null"):
        self.name = name
        self.suite = suite
        self.output_file = name + "-results.txt"
        self.parameters = []
        corrected_suite = self.suite if self.suite != "Null" else self.name
        if name != "Null":
            if corrected_suite not in benchmark.benchmark_status or corrected_suite not in benchmark.results:
                benchmark.benchmark_status[corrected_suite] = {}
                benchmark.results[corrected_suite] = {}
            benchmark.benchmark_status[corrected_suite][self.name] = "Queued"
            benchmark.results[corrected_suite][self.name] = {}
            benchmark.results[corrected_suite][self.name]["general"] = {}
            benchmark.results[corrected_suite][self.name]["specific"] = {}

    def process_generic(self, fp):
        print("processing generic results...", end=" ")
        # for line in fp:
            # TODO: Process pcm info, other info from text file (fp)

    # Overwrite this!
    def process_specific(self):
        print("[Warning] This benchmark has no specific benchmark results!")

    def process():
        results[self.name]["generic"] = process_generic()
        results[self.name]["specific"] = process_specific()

    # Overwrite this if need be!
    def add_parameter(self, name, value):
        self.parameters.append("--" + name + "=" + str(value))

    # Overwrite this!
    def execute(self, local_node=0, remote_node=0):
        print("[ERROR] "+ name + " does not have the way to execute it set up yet!")



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







def main():
    out_fp = open("removemeplease.txt", 'w')
    # cmd = "sudo pcm -csv=pcm.csv --external_program sudo pcm-memory -csv=pcm-memory.csv --external_program "
    cmd = "sudo pcm --external_program sudo pcm-memory --external_program "
    cmd += "sudo numactl --cpunodebind=0 --membind=0 "
    cmd += "./pmbench --mapsize=22000 --setsize=22000 --jobs=10 10"
    subprocess.run("pwd")
    try:
        update = 0
        print(cmd)
        run_cmd = subprocess.Popen(cmd, cwd="../benchmarks/pmbench", stdout=out_fp, shell=True, stderr=subprocess.DEVNULL)
        while run_cmd.poll() is None:
            update += 1
            print("[Status Update " + str(update) + "] " + datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
            time.sleep(2)
    except:
        print("ERROR: Failed to run command!")
        run_cmd.terminate()

    subprocess.run("pwd")

    # img_dnn = tailbench("img-dnn")
    # masstree = tailbench("masstree")
    # img_dnn.add_parameter("QPS", 1)
    # ycsba = ycsb("a")
    # print(img_dnn.parameters)
    # print(masstree.parameters)
    # print(ycsba.parameters)
    # print(tailbench.results)
    return



if __name__=="__main__":
    main()
