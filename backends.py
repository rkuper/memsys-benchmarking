"""""""""""""""""""""""""""""""""""""""""""""""""""
Functions helpful for executing or processing
===================================================
Filename: backends.py
Author: Reese Kuper
Purpose: Functions for executing or processing
"""""""""""""""""""""""""""""""""""""""""""""""""""



"""
Manage Redis: Force redis to a specific NUMA node if need be
"""
def manage_redis(cpu_node, mem_node, script_root, current_directory, action):
    if (action == "start"):
        # Remove any backed up db files to lighten load on starting new server and prevent cloging up storage
        possible_directories = [script_root, redis_directory, current_directory, "../" + current_directory]
        for directory in possible_directories:
            os.remove(directory + "/*.rdb")
        time.sleep(4)

        # Start Redis on specific numa nodes for cpu and memory
        redis_start_cmd = "sudo numactl --cpunodebind=" + str(cpu_node) + " --membind=" + str(mem_node) + \
                            " " + redis_directory + "/redis-server"
        os.system(redis_start_cmd)
        time.sleep(4)

    else:
        os.system(redis_directory + "/redis-cli FLUSHALL")
        time.sleep(2)
        try:
            for line in os.popen("ps ax | grep redis-server | grep -v grep"):
                fields = line.split()
                pid = fields[0]
                os.kill(int(pid), signal.SIGKILL)
            time.sleep(2)
        except:
            print("[ERROR] Could not kill Redis server!")
    return

