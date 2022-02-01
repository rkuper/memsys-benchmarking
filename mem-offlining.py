import os
import sys
import string
import argparse
import re
from subprocess import Popen, PIPE
import numa



def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--size", help = \
            "Desired memory size. This may go slightly above (+/-2GB) when not exact (default = 5GB)", default="5")
    parser.add_argument("-n", "--node", help = \
            "Node to change memory size (default = 0)", default="0")
    args = parser.parse_args()

    mem_dir='/sys/devices/system/memory'
    memlist = [re.findall("\d+", mem)[0] for mem in os.listdir(mem_dir) \
                if (os.path.isdir(os.path.join(mem_dir, mem)) and "memory" in mem)]

    node_mems = {}
    for numa_node in range(numa.get_max_node()+1):
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
    original_node_mem = numa.get_node_size(int(args.node))[1] * 0.95
    current_node_mem = numa.get_node_size(int(args.node))[1] * 0.95
    for mem in node_mems["node" + str(args.node)]:
        print("Offlining 'memory" + mem + "'...", end=" ")
        os.system("sudo sh -c 'echo 0 > /sys/devices/system/memory/memory" + mem + "/online'")
        print("Done!")
        current_node_mem = numa.get_node_size(int(args.node))[1] * 0.95


    # If the current memory size is still more than desired size, we tried I guess :/
    if (current_node_mem//1000000000) < int(args.size):
        for mem in node_mems["node" + str(args.node)]:
            if (current_node_mem/1000000000) > (int(args.size)):
                break
            print("Onlining 'memory" + mem + "'...", end=" ")
            os.system("sudo sh -c 'echo 1 > /sys/devices/system/memory/memory" + mem + "/online'")
            print("Done!")
            current_node_mem = numa.get_node_size(int(args.node))[1] * 0.95
    else:
        print("[WARNING] Unable to decrease memory on node" + args.node + " to " + args.size + "GB")


    # Results
    print("===============================\n")
    print("RAM on node" + args.node + " before: " + str(round(original_node_mem/1000000000)) + "GB")
    print("RAM on node" + args.node + " after: " + str(round(current_node_mem/1000000000)) + "GB")



if __name__=="__main__":
    main()
