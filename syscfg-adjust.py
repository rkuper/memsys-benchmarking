import os
import sys
import string
import argparse
import re
import numa



def mem_capacity(target_node, target_capacity):
    mem_dir='/sys/devices/system/memory'
    memlist = [re.findall("\d+", mem)[0] for mem in os.listdir(mem_dir) \
                if (os.path.isdir(os.path.join(mem_dir, mem)) and "memory" in mem)]

    node_mems = {}
    for numa_node in range(numa.info.get_max_node()+1):
        node_mems["node" + str(numa_node)] = []

    # Adds mem blocks to their respective dictionary list
    for mem in memlist:
        for in_mem_dir in os.listdir(mem_dir + "/memory" + mem):
            online_status = True
            with open(mem_dir + "/memory" + mem + "/online") as mem_status:
                for line in mem_status:
                    if online_status == "0":
                        online_status = False
            if "node" in in_mem_dir and online_status:
                node_mems[in_mem_dir].append(mem)
                break


    # Offline as much as possible
    original_node_mem = numa.memory.node_memory_info(int(target_node))[1] * 0.95
    current_node_mem = numa.memory.node_memory_info(int(target_node))[1] * 0.95
    if (current_node_mem/1000000000) > int(target_capacity):
        for mem in node_mems["node" + str(target_node)]:
            print("Offlining 'memory" + mem + "'...", end=" ")
            os.system("sudo sh -c 'echo 0 > /sys/devices/system/memory/memory" + mem + "/online'")
            print("Done!")
            current_node_mem = numa.memory.node_memory_info(int(target_node))[1] * 0.95
            if (current_node_mem/1000000000) < int(target_capacity):
                print("Onlining 'memory" + mem + "'...", end=" ")
                os.system("sudo sh -c 'echo 1 > /sys/devices/system/memory/memory" + mem + "/online'")
                print("Done!")
                current_node_mem = numa.memory.node_memory_info(int(target_node))[1] * 0.95
                break
    else:
        print("[WARNING] Already below target node capacity (~" + current_node_mem/1000000000 + "GB)")

    # Results
    print("===============================\n")
    print("RAM on node" + target_node + " before: " + str(round(original_node_mem/1000000000)) + "GB")
    print("RAM on node" + target_node + " after: " + str(round(current_node_mem/1000000000)) + "GB")
    return



def hyperthreading(disable):
    cpu_dir = "/sys/devices/system/cpu"
    cpu_list = sorted(list(filter(None, [re.findall("cpu[0-9]+"[3:], cpu) for cpu in os.listdir(cpu_dir)])))
    num_cpus_before = os.cpu_count()
    cpu_pairs = {}

    if disable:
        # Gathering cpu list
        for cpu in cpu_list:
            with open(cpu_dir + "/cpu" + cpu[0] + "/topology/thread_siblings_list") as cpu_sibling:
                for line in cpu_sibling:
                    (real_cpu, ht_cpu) = line.strip().split(",")
                    cpu_pairs[real_cpu] = ht_cpu

        # Begin offlining
        for cpu_pair in cpu_pairs:
            print("Offlining 'cpu" + cpu_pairs[cpu_pair] + "'...", end=" ")
            os.system("sudo sh -c 'echo 0 > /sys/devices/system/cpu/cpu" + cpu_pairs[cpu_pair] + "/online'")
            print("Done!")
    else:
        # Online all available cpus
        for cpu in cpu_list:
            print("Onlining 'cpu" + cpu[0] + "'...", end=" ")
            os.system("sudo sh -c 'echo 1 > /sys/devices/system/cpu/cpu" + cpu[0] + "/online'")
            print("Done!")
    print("")

    num_cpus_after = os.cpu_count()
    if (num_cpus_after == num_cpus_before):
        print("[WARNING] No change in the number of onlined CPUs!")
    print("Total number of onlined CPU's before: " + str(num_cpus_before))
    print("Total number of onlined CPU's after: " + str(num_cpus_after))
    return



def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-m", "--offline_mem", help = \
            "Change system visible RAM capacity (default = false)", action='store_true')
    parser.add_argument("-c", "--capacity", help = \
            "Desired memory capacity. This may go slightly above (+/-2GB) when not exact (default = 7GB)", default="7")
    parser.add_argument("-n", "--node", help = \
            "Node to change memory size (default = 0)", default="0")
    parser.add_argument("-H,", "--change_hyperthreading", help = \
            "Allow changes to current hyperthreading status (default = false)", action='store_true')
    parser.add_argument("-d", "--disable_hyperthreading", help = \
            "Offline visible hyperthreaded_cores (default = false)", action='store_true')
    args = parser.parse_args()

    if args.offline_mem:
        mem_capacity(args.node, args.capacity)

    if args.change_hyperthreading:
        hyperthreading(args.disable_hyperthreading)
    return



if __name__=="__main__":
    main()
