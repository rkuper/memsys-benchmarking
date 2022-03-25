#!/bin/bash

# Collect shell script arguments
POSITIONAL=()
while [[ $# -gt 0 ]]; do
  key="$1"

  case $key in
    -b|--benchmarks)
      BENCHMARKS="$2"
      shift; shift
      ;;
    -m|--mem_configs)
      MEM_CONFIGS="$2"
      shift; shift
      ;;
    -s|--samples)
      TOTAL_SAMPLES="$2"
      shift; shift
      ;;
    -f|--output_file)
      OUTPUT_FILE="$2"
      shift; shift
      ;;
    -d|--output_dir)
      OUTPUT_DIR="$2"
      shift; shift
      ;;
    -l|--local_node)
      LOCAL_NODE="$2"
      shift; shift
      ;;
    -r|--remote_node)
      REMOTE_NODE="$2"
      shift; shift
      ;;
    -c|--context)
      CONTEXT="$2"
      shift
      ;;
    -e|--execute_benchmarks)
      EXECUTE_BENCHMARKS="$2"
      shift
      ;;
    -p|--process)
      PROCESS="$2"
      shift
      ;;
    *)
      POSITIONAL+=("$1")
      shift
      ;;
  esac
done

MAIN_DIR=`pwd`
REDIS_DIR=${MAIN_DIR}/tools/redis/src

BENCHMARKS=$([ "$BENCHMARKS" == "all" -o -z "${BENCHMARKS+x}" -o "$BENCHMARKS" == "" ] \
  && echo "tailbench ycsb memtier pmbench cachebench" || echo "$BENCHMARKS")
BENCHMARKS=($BENCHMARKS)

declare -a TAIL_BENCHMARKS=("img-dnn" "masstree" "moses" "silo" "specjbb" "sphinx")
declare -a YCSB_BENCHMARKS=("a" "b" "c" "f" "d")

declare -a TAIL_CONFIGS=("integrated" "networked")
declare -a YCSB_CONFIGS=("load" "run")

NUMA_NODES=`numactl -H | awk '/available:/ {if ($2 > 1) {print "True"} else {print "False"}}'`
if [ $NUMA_NODES == "False" ]; then
  MEM_CONFIGS="local"
else
  MEM_CONFIGS=$([ "$MEM_CONFIGS" == "all" -o -z "${MEM_CONFIGS+x}" -o "$MEM_CONFIGS" == "" ] \
    && echo "local remote both" || echo "$MEM_CONFIGS")
  MEM_CONFIGS=($MEM_CONFIGS)
fi

LOCAL_NODE=$([ -z "${LOCAL_NODE+x}" -o "$LOCAL_NODE" == "" ] \
  && echo "0" || echo "$LOCAL_NODE")
REMOTE_NODE=$([ -z "${REMOTE_NODE+x}" -o "$REMOTE_NODE" == "" ] \
  && echo "1" || echo "$REMOTE_NODE")

REGEX_NUM='^[0-9]+$'
TOTAL_SAMPLES=$([[ -v TOTAL_SAMPLES && $TOTAL_SAMPLES =~ $REGEX_NUM ]] && echo "$TOTAL_SAMPLES" || echo "1")

KEEP_LOGS=$([ -v KEEP_LOGS -o -z KEEP_LOGS ] && echo "true" || echo "false")
CONTEXT=$([ -v CONTEXT -o -z CONTEXT ] && echo "true" || echo "false")
EXECUTE_BENCHMARKS=$([ -v EXECUTE_BENCHMARKS -o -z EXECUTE_BENCHMARKS ] && echo "true" || echo "false")
PROCESS=$([ -v PROCESS -o -z PROCESS ] && echo "true" || echo "false")
OUTPUT_FILE=$([ -v OUTPUT_FILE ] && echo "$OUTPUT_FILE" || echo "results.txt")
OUTPUT_DIR=$([ -v OUTPUT_DIR ] && echo "$OUTPUT_DIR" || echo "results")
OUTPUT_PATH=`pwd`/${OUTPUT_DIR}/${OUTPUT_FILE}

declare -a TAIL_TYPES=("Queue" "Service" "Sojourn")
declare -a YCSB_TYPES=("INSERT" "READ" "UPDATE" "READ-MODIFY-WRITE")
declare -a MEMTIER_TYPES=("Sets" "Gets" "Totals")
declare -a CACHEBENCH_TYPES=("get" "set" "del")

# NOTE: MEMTIER_METRICS are their indices!
declare -a TAIL_METRICS=("50th" "75th" "90th" "95th" "99th" "99.9th" "99.99th" "Max" "Mean")
declare -a YCSB_METRICS=("50th" "75th" "90th" "95th" "99th" "99.9Per" "99.99Per" "MaxLatency" "AverageLatency")
declare -a MEMTIER_METRICS=("6" "7" "8" "9" "10" "11" "12" "13" "5" "2")




####################################
#            Benchmarks            #
####################################

# $1 = number of runs
run_tailbench() {
  cd tailbench
  for TAIL_BENCHMARK in "${TAIL_BENCHMARKS[@]}"; do
    echo "-=========================="
    echo "-=        ${TAIL_BENCHMARK}         ="
    echo "-=========================="
    echo ""

    cd $TAIL_BENCHMARK

    for MEM_CONFIG in "${MEM_CONFIGS[@]}"; do
      BALANCING=$([ "$MEM_CONFIG" == "both" ] && echo "1" || echo "0")
      sudo sysctl -w kernel.numa_balancing=${BALANCING}; sleep 2
      CPU_NODE=$([ "$MEM_CONFIG" == "local" ] && echo "${LOCAL_NODE}" || echo "${REMOTE_NODE}")
      MEM_NODE=$([ "$MEM_CONFIG" == "local" ] && echo "${LOCAL_NODE}" || \
        ([ "$MEM_CONFIG" == "remote" ] && echo "${LOCAL_NODE}" || echo "${REMOTE_NODE},${LOCAL_NODE}"))
      for TAIL_CONFIG in "${TAIL_CONFIGS[@]}"; do
        for SAMPLE in $(eval echo {1..$1}); do
          echo "${TAIL_CONFIG} - ${MEM_CONFIG} - ${SAMPLE}:"
          echo "-------------------"
          # NUMA counters before run:
          NUMA_HIT_BEFORE=`awk '/numa_hit/ {print $2}' /proc/vmstat`
          NUMA_MISS_BEFORE=`awk '/numa_miss/ {print $2}' /proc/vmstat`
          NUMA_MIGRATED_BEFORE=`awk '/numa_pages_migrated/ {print $2}' /proc/vmstat`
          NUMA_SUCCESS_BEFORE=`awk '/pgmigrate_success/ {print $2}' /proc/vmstat`
          NUMA_FAIL_BEFORE=`awk '/pgmigrate_fail/ {print $2}' /proc/vmstat`
          NUMA_LOCAL_BEFORE=`awk '/numa_local/ {print $2}' /proc/vmstat`
          NUMA_FOREIGN_BEFORE=`awk '/numa_foreign/ {print $2}' /proc/vmstat`
          sudo pcm --external_program sudo pcm-memory --external_program \
            sudo numactl --cpunodebind=${CPU_NODE} --membind=${MEM_NODE} \
            ./run_${TAIL_CONFIG}.sh > pcm_tmp.txt
          # NUMA counters after run:
          NUMA_HIT=`expr $(awk '/numa_hit/ {print $2}' /proc/vmstat) - $NUMA_HIT_BEFORE`
          NUMA_MISS=`expr $(awk '/numa_miss/ {print $2}' /proc/vmstat) - $NUMA_MISS_BEFORE`
          NUMA_MIGRATED=`expr $(awk '/numa_pages_migrated/ {print $2}' /proc/vmstat) - $NUMA_MIGRATED_BEFORE`
          NUMA_SUCCESS=`expr $(awk '/pgmigrate_success/ {print $2}' /proc/vmstat) - $NUMA_SUCCESS_BEFORE`
          NUMA_FAIL=`expr $(awk '/pgmigrate_fail/ {print $2}' /proc/vmstat) - $NUMA_FAIL_BEFORE`
          NUMA_LOCAL=`expr $(awk '/numa_local/ {print $2}' /proc/vmstat) - $NUMA_LOCAL_BEFORE`
          NUMA_FOREIGN=`expr $(awk '/numa_foreign/ {print $2}' /proc/vmstat) - $NUMA_FOREIGN_BEFORE`
          echo "numa_hits: $NUMA_HIT" >> pcm_tmp.txt
          echo "numa_hit_rate: \
                  `awk 'BEGIN {print ('"$NUMA_HIT"' / ('"$NUMA_HIT"' + '"$NUMA_MISS"'))}'`" >> pcm_tmp.txt
          echo "numa_migrations: ${NUMA_MIGRATED}" >> pcm_tmp.txt
          echo "numa_migration_success_rate: \
                  `awk 'BEGIN {print ('"$NUMA_SUCCESS"' / ('"$NUMA_SUCCESS"' + '"$NUMA_FAIL"'))}'`" >> pcm_tmp.txt
          echo "numa_local: $NUMA_LOCAL" >> pcm_tmp.txt
          echo "numa_percent_local: \
                  `awk 'BEGIN {print ('"$NUMA_LOCAL"' / ('"$NUMA_LOCAL"' + '"$NUMA_FOREIGN"'))}'`" >> pcm_tmp.txt
          if [ -f "lats.bin" ]; then
            python3 ../utilities/parselats.py lats.bin > tmp.txt
            cat tmp.txt pcm_tmp.txt > ../../${OUTPUT_DIR}/tailbench/${TAIL_BENCHMARK}/${MEM_CONFIG}_${TAIL_CONFIG}_${SAMPLE}.txt
            rm lats.bin
          fi
          echo ""
        done # End of run
      done # End of tail config (integrated vs networked run)
    done # End of mem config (local, remote, etc.)
    cd ..
    echo ""; echo ""
  done # End of tailbench benchmarks
  cd ..
}

# $1 = number of runs
run_ycsb() {
  cd ycsb
  for YCSB_BENCHMARK in "${YCSB_BENCHMARKS[@]}"; do
    echo "-=============================="
    echo "-=        Workload-${YCSB_BENCHMARK}         ="
    echo "-=============================="
    echo ""

    for MEM_CONFIG in "${MEM_CONFIGS[@]}"; do
      BALANCING=$([ "$MEM_CONFIG" == "both" ] && echo "1" || echo "0")
      sudo sysctl -w kernel.numa_balancing=${BALANCING}; sleep 2
      CPU_NODE=$([ "$MEM_CONFIG" == "local" ] && echo "${LOCAL_NODE}" || echo "${REMOTE_NODE}")
      MEM_NODE=$([ "$MEM_CONFIG" == "local" ] && echo "${LOCAL_NODE}" || \
        ([ "$MEM_CONFIG" == "remote" ] && echo "${LOCAL_NODE}" || echo "${REMOTE_NODE},${LOCAL_NODE}"))
      for SAMPLE in $(eval echo {1..$TOTAL_SAMPLES}); do
        sudo rm -f ${REDIS_DIR}/*.rdb; sudo rm -f ./*.rdb; sudo rm -f ../*.rdb; sleep 4
        sudo numactl --cpunodebind=${CPU_NODE} --membind=${MEM_NODE} ${REDIS_DIR}/redis-server & sleep 4
        for YCSB_CONFIG in "${YCSB_CONFIGS[@]}"; do
          echo "${YCSB_CONFIG} - ${MEM_CONFIG} - ${SAMPLE}:"
          echo "-------------------"
          sudo ./run_ycsb.sh ${CPU_NODE} ${MEM_NODE} ${YCSB_BENCHMARK} ${YCSB_CONFIG}
          mv ycsb-results.txt ../${OUTPUT_DIR}/ycsb/${YCSB_BENCHMARK}/${MEM_CONFIG}_${YCSB_CONFIG}_${SAMPLE}.txt
          echo ""
        done # End of YCSB config (run or load)
        ${REDIS_DIR}/redis-cli FLUSHALL
        sudo pkill redis-server & sleep 4
      done # End of run
    done # End of mem config (local, remote, etc.)
    echo ""; echo ""
  done # End of YCSB benchmark (ex. workloada)
  cd ..
}

# $1 = number of runs
run_memtier() {
  cd memtier
  echo "-=============================="
  echo "-=      General Memtier       ="
  echo "-=============================="
  echo ""

  for MEM_CONFIG in "${MEM_CONFIGS[@]}"; do
    BALANCING=$([ "$MEM_CONFIG" == "both" ] && echo "1" || echo "0")
    sudo sysctl -w kernel.numa_balancing=${BALANCING}; sleep 2
    CPU_NODE=$([ "$MEM_CONFIG" == "local" ] && echo "${LOCAL_NODE}" || echo "${REMOTE_NODE}")
    MEM_NODE=$([ "$MEM_CONFIG" == "local" ] && echo "${LOCAL_NODE}" || \
      ([ "$MEM_CONFIG" == "remote" ] && echo "${LOCAL_NODE}" || echo "${REMOTE_NODE},${LOCAL_NODE}"))
    for SAMPLE in $(eval echo {1..$TOTAL_SAMPLES}); do
      sudo rm -f ${REDIS_DIR}/*.rdb; sudo rm -f ./*.rdb; sudo rm -f ../*.rdb; sleep 4
      sudo numactl --cpunodebind=${CPU_NODE} --membind=${MEM_NODE} ${REDIS_DIR}/redis-server & sleep 4
      echo "${MEM_CONFIG} - ${SAMPLE}:"
      echo "-------------------"
      sudo ./run_memtier.sh ${CPU_NODE} ${MEM_NODE}
      mv memtier-results.txt ../${OUTPUT_DIR}/memtier/${MEM_CONFIG}_${SAMPLE}.txt
      ${REDIS_DIR}/redis-cli FLUSHALL
      sudo pkill redis-server & sleep 4
      echo ""
    done # End of run
    echo ""; echo ""
  done # End of mem config (local, remote, etc.)
  cd ..
}

# $1 = number of runs
run_pmbench() {
  cd pmbench
  echo "-=============================="
  echo "-=      General PMBench       ="
  echo "-=============================="
  echo ""

  for MEM_CONFIG in "${MEM_CONFIGS[@]}"; do
    BALANCING=$([ "$MEM_CONFIG" == "both" ] && echo "1" || echo "0")
    sudo sysctl -w kernel.numa_balancing=${BALANCING}; sleep 2
    CPU_NODE=$([ "$MEM_CONFIG" == "local" ] && echo "${LOCAL_NODE}" || echo "${REMOTE_NODE}")
    MEM_NODE=$([ "$MEM_CONFIG" == "local" ] && echo "${LOCAL_NODE}" || \
      ([ "$MEM_CONFIG" == "remote" ] && echo "${LOCAL_NODE}" || echo "${REMOTE_NODE},${LOCAL_NODE}"))
    for SAMPLE in $(eval echo {1..$TOTAL_SAMPLES}); do
      echo "${MEM_CONFIG} - ${SAMPLE}:"
      echo "-------------------"
      sudo ./run_pmbench.sh ${CPU_NODE} ${MEM_NODE}
      mv pmbench-results.txt ../${OUTPUT_DIR}/pmbench/${MEM_CONFIG}_${SAMPLE}.txt
      echo ""
    done # End of run
    echo ""; echo ""
  done # End of mem config (local, remote, etc.)
  cd ..
}

# $1 = number of runs
run_cachebench() {
  cd cachelib/opt/cachelib/bin
  echo "-================================="
  echo "-=      General Cachebench       ="
  echo "-================================="
  echo ""

  for MEM_CONFIG in "${MEM_CONFIGS[@]}"; do
    BALANCING=$([ "$MEM_CONFIG" == "both" ] && echo "1" || echo "0")
    sudo sysctl -w kernel.numa_balancing=${BALANCING}; sleep 2
    CPU_NODE=$([ "$MEM_CONFIG" == "local" ] && echo "${LOCAL_NODE}" || echo "${REMOTE_NODE}")
    MEM_NODE=$([ "$MEM_CONFIG" == "local" ] && echo "${LOCAL_NODE}" || \
      ([ "$MEM_CONFIG" == "remote" ] && echo "${LOCAL_NODE}" || echo "${REMOTE_NODE},${LOCAL_NODE}"))
    for SAMPLE in $(eval echo {1..$TOTAL_SAMPLES}); do
      echo "${MEM_CONFIG} - ${SAMPLE}:"
      echo "-------------------"
      sudo ./run_cachebench.sh ${CPU_NODE} ${MEM_NODE}
      mv cachebench-results.txt ../../../../${OUTPUT_DIR}/cachebench/${MEM_CONFIG}_${SAMPLE}.txt
      echo ""
    done # End of run
    echo ""; echo ""
  done # End of mem config (local, remote, etc.)
  cd ../../../../
}

if [ "$EXECUTE_BENCHMARKS" == "true" ]; then
  for BENCHMARK in "${BENCHMARKS[@]}"; do
    echo "##########################"
    echo "#                         #"
    echo "#        ${BENCHMARK}         #"
    echo "#                         #"
    echo "##########################"
    echo ""

    case $BENCHMARK in
      tailbench)
        run_tailbench ${TOTAL_SAMPLES}
        ;;
      ycsb)
        run_ycsb ${TOTAL_SAMPLES}
        ;;
      memtier)
        run_memtier ${TOTAL_SAMPLES}
        ;;
      pmbench)
        run_pmbench ${TOTAL_SAMPLES}
        ;;
      cachebench)
        run_cachebench ${TOTAL_SAMPLES}
        ;;
      *)
        echo "Unrecognized Benchmark"
        ;;
    esac
    echo ""
  done # End of benchmark suites
fi



####################################
#            Processing            #
####################################

# General helper for parsing general data
# $1 = Wildcard log files for averaging results across runs
# $2 = MEM_CONFIG
# $3 = 'getline' added for getting correct data
# $4 = Can get NUMA data (tailbench cannot get numa stat info for it, so skip that part)
general_parsing() {
  PCM_MEM_CONFIG_SEARCH=$([ "$2" == "local" ] && echo "NODE 0 Mem" || \
           ([ "$2" == "remote" ] && echo "NODE 0 Mem" || echo "System"))
  THROUGHPUT_READ_INDEX=$([ "$2" == "both" ] && echo "5" || echo "8")
  THROUGHPUT_WRITE_INDEX=$([ "$2" == "both" ] && echo "5" || echo "7")

  if [ "$CONTEXT" != "true" ]; then echo "Overall:"; fi

  if ls $1 1> /dev/null 2>&1; then
    # PCM Data:
    if [ "$CONTEXT" == "true" ]; then echo -n "[OVERALL] LLCRDMISSLAT(ns): "; fi
    echo `awk '/LLCRDMISSLAT / {getline; getline; '"$3"' sum += $9; n++} END \
      { if (n > 0) {print sum / n;} else {print "Null"} }' $1`

    if [ "$CONTEXT" == "true" ]; then echo -n "[OVERALL] ${PCM_MEM_CONFIG_SEARCH} Read Throughput(MB/s): "; fi
    echo `awk '/'"$PCM_MEM_CONFIG_SEARCH"' Read/ {sum += $'"$THROUGHPUT_READ_INDEX"'; n++} END \
      { if (n > 0) {print sum / n;} else {print "Null"} }' $1`

    if [ "$CONTEXT" == "true" ]; then echo -n "[OVERALL] ${PCM_MEM_CONFIG_SEARCH} Write Throughput(MB/s): "; fi
    echo `awk '/'"$PCM_MEM_CONFIG_SEARCH"' Write/ {sum += $'"$THROUGHPUT_WRITE_INDEX"'; n++} END \
      { if (n > 0) {print sum / n;} else {print "Null"} }' $1`

    if [ "$CONTEXT" == "true" ]; then echo -n "[OVERALL] DIMM Energy(J): "; fi
    echo `awk '/DIMM energy / {getline; getline; sum += $8; n++} END \
      { if (n > 0) {print sum / n;} else {print "Null"} }' $1`

    GETLINES=" getline;"
    for FACTOR in $(eval echo {1..58}); do GETLINES="$GETLINES getline;"; done
    GETLINES=$([ "$2" == "local" ] && echo "$GETLINES" ||
            ([ "$2" == "remote" ] && echo "$GETLINES getline;" || echo "$GETLINES getline; getline; getline;"))
    FULL_SEARCH="Core \(SKT\) "
    if [ "$CONTEXT" == "true" ]; then echo -n "[OVERALL] L3HIT: "; fi
    echo `awk '/'"$FULL_SEARCH"'/ {'"$GETLINES"' sum += $11; n++} END \
      { if (n > 0) { print sum / n } else {print "Null"} }' $1`

    # VMStat Data:
    if [ "$4" == "true" ]; then
      if [ "$CONTEXT" == "true" ]; then echo -n "[OVERALL] NUMA Hits: "; fi
      echo `awk '/numa_hits/ {sum += $2; n++} END { if (n > 0) {print sum / n;} else {print "Null"} }' $1`

      if [ "$CONTEXT" == "true" ]; then echo -n "[OVERALL] NUMA Hit Rate: "; fi
      echo `awk '/numa_hit_rate/ {sum += $2; n++} END { if (n > 0) {print sum / n;} else {print "Null"} }' $1`

      if [ "$CONTEXT" == "true" ]; then echo -n "[OVERALL] NUMA Migrations: "; fi
      echo `awk '/numa_migrations/ {sum += $2; n++} END { if (n > 0) {print sum / n;} else {print "Null"} }' $1`

      if [ "$CONTEXT" == "true" ]; then echo -n "[OVERALL] NUMA Migration Success Rate: "; fi
      echo `awk '/numa_migration_success_rate/ {sum += $2; n++} END { if (n > 0) {print sum / n;} else {print "Null"} }' $1`

      if [ "$CONTEXT" == "true" ]; then echo -n "[OVERALL] NUMA Local Accesses: "; fi
      echo `awk '/numa_local/ {sum += $2; n++} END { if (n > 0) {print sum / n;} else {print "Null"} }' $1`

      if [ "$CONTEXT" == "true" ]; then echo -n "[OVERALL] NUMA Percent Local: "; fi
      echo `awk '/numa_percent_local/ {sum += $2; n++} END { if (n > 0) {print sum / n;} else {print "Null"} }' $1`
    else
      echo "Null"; echo "Null"; echo "Null"; echo "Null"; echo "Null"; echo "Null"
    fi


  else
    # PCM Data
    echo "Null"; echo "Null"; echo "Null"; echo "Null"; echo "Null"

    # VMStat Data
    echo "Null"; echo "Null"; echo "Null"; echo "Null"; echo "Null"; echo "NULL"
  fi
}



if [ "$PROCESS" == "true" ]; then
 echo "Porcessing..."
  {
    cd ${OUTPUT_DIR}
    for BENCHMARK in "${BENCHMARKS[@]}"; do

      echo "##########################"
      echo "#                         #"
      echo "#        ${BENCHMARK}         #"
      echo "#                         #"
      echo "##########################"
      echo ""
      cd $BENCHMARK

      case $BENCHMARK in
        tailbench)
          for TAIL_BENCHMARK in "${TAIL_BENCHMARKS[@]}"; do
            echo "-============================"
            echo "-=        ${TAIL_BENCHMARK}         ="
            echo "-============================"
            echo ""
            cd ${TAIL_BENCHMARK}

            for MEM_CONFIG in "${MEM_CONFIGS[@]}"; do
              for TAIL_CONFIG in "${TAIL_CONFIGS[@]}"; do
                echo "$MEM_CONFIG $TAIL_CONFIG"; echo "------------------"

                # Metrics for tail latency reported by tailbench's harness
                ##########################################################
                for TAIL_TYPE in "${TAIL_TYPES[@]}"; do
                 if [ "$CONTEXT" == "false" ]; then
                    echo "$TAIL_TYPE:"
                  fi
                  for TAIL_METRIC in "${TAIL_METRICS[@]}"; do
                    if ls ./${MEM_CONFIG}_${TAIL_CONFIG}_*.txt 1> /dev/null 2>&1; then
                      if [ "$CONTEXT" == "true" ]; then echo -n "[$TAIL_TYPE] $TAIL_METRIC: "; fi
                      echo `awk '/\['"$TAIL_TYPE"'\] '"$TAIL_METRIC"'/ {sum += $5; n++} END \
                        { if (n > 0) {print sum / n} else {print "Null"}}' \
                        ${MEM_CONFIG}_${TAIL_CONFIG}_*.txt`
                    else
                      echo "Null"
                    fi
                  done
                echo ""
                done

                SOCKET_PCM=$([ "$MEM_CONFIG" == "local" ] && echo "" || echo "getline;")
                PCM_FILES=${MEM_CONFIG}_${TAIL_CONFIG}_*.txt
                general_parsing "${PCM_FILES}" "${MEM_CONFIG}" "${SOCKET_PCM}" "true"
                echo ""
              done
              echo ""; echo "";
            done
            cd ..
          done
          ;;


        ycsb)
          for YCSB_BENCHMARK in "${YCSB_BENCHMARKS[@]}"; do
            echo "-============================="
            echo "-=        Workload ${YCSB_BENCHMARK}         ="
            echo "-============================="
            echo ""
            cd ${YCSB_BENCHMARK}

            for MEM_CONFIG in "${MEM_CONFIGS[@]}"; do
              for YCSB_CONFIG in "${YCSB_CONFIGS[@]}"; do
                echo "$MEM_CONFIG - $YCSB_CONFIG:"
                echo "-============"

                # Metrics for tail latency reported by ycsb
                #############################################

                for YCSB_TYPE in "${YCSB_TYPES[@]}"; do
                  if [ "$CONTEXT" == "false" ]; then echo "$YCSB_TYPE:"; fi
                  for YCSB_METRIC in "${YCSB_METRICS[@]}"; do
                    if ls ./${MEM_CONFIG}_${YCSB_CONFIG}_*.txt 1> /dev/null 2>&1; then
                      if [ "$CONTEXT" == "true" ]; then echo -n "[$YCSB_TYPE] $YCSB_METRIC (ms): "; fi
                      echo `awk '/\['"$YCSB_TYPE"'\], '"$YCSB_METRIC"'/ {sum += $3; n++} END \
                        {if (n > 0) {print sum / n} else {print "Null"}}' \
                        ${MEM_CONFIG}_${YCSB_CONFIG}_*.txt`
                    else
                      echo "Null"
                    fi
                  done # End of YCSB Metrics (Averages, tail latencies, etc.)
                  echo ""
                done # End of YCSB Type (Insert, Update, etc.)

                if [ "$CONTEXT" == "false" ]; then echo "YCSB Overall:"; else echo "[OVERALL] Throughput (ops/sec)"; fi
                if ls ./${MEM_CONFIG}_${YCSB_CONFIG}_*.txt 1> /dev/null 2>&1; then
                  echo `awk '/OVERALL], Throughput/ {sum += $3; n++} END \
                    { if (n > 0) { print sum / n } else {print "Null"} }' ${MEM_CONFIG}_${YCSB_CONFIG}_*.txt`
                else
                  echo "Null"
                fi
                echo ""

                SOCKET_PCM=$([ "$MEM_CONFIG" == "local" ] && echo "" || echo "getline;")
                PCM_FILES=${MEM_CONFIG}_${YCSB_CONFIG}_*.txt
                general_parsing "${PCM_FILES}" "${MEM_CONFIG}" "${SOCKET_PCM}" "true"
                echo ""
              done
              echo ""; echo "";
            done
            cd ..
          done
          ;;


        memtier)
          echo "-=========================="
          echo "-=    GENERAL MEMTIER     ="
          echo "-=========================="
          echo ""

          for MEM_CONFIG in "${MEM_CONFIGS[@]}"; do
            echo "$MEM_CONFIG:"
            echo "--------------"
              for MEMTIER_TYPE in "${MEMTIER_TYPES[@]}"; do
                echo "$MEMTIER_TYPE:"
                for MEMTIER_METRIC in "${MEMTIER_METRICS[@]}"; do
                  if ls ./${MEM_CONFIG}_*.txt 1> /dev/null 2>&1; then
                    echo `awk '/'"$MEMTIER_TYPES"'/ {sum += $'"$MEMTIER_METRIC"'; n++} END \
                      {if (n > 0) {print sum / n} else {print "Null"}}' \
                      ${MEM_CONFIG}_*.txt`
                  else
                    echo "Null"
                  fi
                done
                echo ""
              done

              SOCKET_PCM=$([ "$MEM_CONFIG" == "local" ] && echo "" || echo "getline;")
              PCM_FILES=${MEM_CONFIG}_*.txt
              general_parsing "${PCM_FILES}" "${MEM_CONFIG}" "${SOCKET_PCM}" "true"
              echo ""; echo ""; echo ""
          done
          ;;

        pmbench)
          echo "-=========================="
          echo "-=    GENERAL PMBENCH     ="
          echo "-=========================="
          echo ""

          for MEM_CONFIG in "${MEM_CONFIGS[@]}"; do
            echo "$MEM_CONFIG:"
            echo "--------------"

						# Histogram of read and write page latencies
              declare -a IO_MODES=("Read" "Write")
              for IO_MODE in "${IO_MODES[@]}"; do
                echo "$IO_MODE:"
                GETLINES=" getline;"
                  for FACTOR in $(eval echo {1..13}); do
                    if ls ./${MEM_CONFIG}_*.txt 1> /dev/null 2>&1; then
                      echo `awk '/'"$IO_MODE"':/ {'"$GETLINES"' sum += $3; n++} END \
                        { if (n > 0) {print sum / n;} else {print "Null"} }' ${MEM_CONFIG}_*.txt`
	                    GETLINES="$GETLINES getline;"
                   else
                     echo "Null"
                   fi
                  done
                echo ""
              done

              if ls ./${MEM_CONFIG}_*.txt 1> /dev/null 2>&1; then
              echo "Average:"
                echo `awk '/Net average page latency/ {sum += $7; n++} END \
                  { if (n > 0) {print sum / n;} else {print "Null"} }' ${MEM_CONFIG}_*.txt`
              else
                echo "Null"
              fi
              echo ""


              SOCKET_PCM=$([ "$MEM_CONFIG" == "local" ] && echo "" || echo "getline;")
              PCM_FILES=${MEM_CONFIG}_*.txt
              general_parsing "${PCM_FILES}" "${MEM_CONFIG}" "${SOCKET_PCM}" "true"
              echo ""; echo ""; echo ""
          done
          ;;

        cachebench)
          echo "-============================="
          echo "-=    GENERAL CACHEBENCH     ="
          echo "-============================="
          echo ""

          for MEM_CONFIG in "${MEM_CONFIGS[@]}"; do
            echo "$MEM_CONFIG:"
            echo "--------------"
              for CACHEBENCH_TYPE in "${CACHEBENCH_TYPES[@]}"; do
                echo "$CACHEBENCH_TYPE:"
                if ls ./${MEM_CONFIG}_*.txt 1> /dev/null 2>&1; then
                  echo `awk '/'"$CACHEBENCH_TYPE"'       / {gsub(/,|\/|s/, "", $3); sum += $3; n++} END \
                    {if (n > 0) {print sum / n} else {print "Null"}}' \
                    ${MEM_CONFIG}_*.txt`
                else
                  echo "Null"
                fi
                echo ""
              done

              SOCKET_PCM=$([ "$MEM_CONFIG" == "local" ] && echo "" || echo "getline;")
              PCM_FILES=${MEM_CONFIG}_*.txt
              general_parsing "${PCM_FILES}" "${MEM_CONFIG}" "${SOCKET_PCM}" "true"
              echo ""; echo ""; echo ""
          done
          ;;

        *)
          echo "Unrecognized Benchmrk"
          ;;
      esac
      cd ..
    done
    cd ..
  } > ${OUTPUT_PATH}
fi
