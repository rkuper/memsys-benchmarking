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
    -r|--runs)
      TOTAL_RUNS="$2"
      shift; shift
      ;;
    -o|--output)
      OUTPUT_FILE="$2"
      shift; shift
      ;;
    -d|--dram_node)
      DRAM_NODE="$2"
      shift; shift
      ;;
    -n|--pmem_node)
      PMEM_NODE="$2"
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
  && echo "tailbench ycsb memtier" || echo "$BENCHMARKS")
BENCHMARKS=($BENCHMARKS)

declare -a TAIL_BENCHMARKS=("img-dnn" "masstree" "moses" "silo" "specjbb" "sphinx" "xapian")
declare -a YCSB_BENCHMARKS=("a" "b" "c" "f" "d")
declare -a MEMTIER_BENCHMARKS=("general")

declare -a TAIL_CONFIGS=("integrated" "networked")
declare -a YCSB_CONFIGS=("load" "run")

MEM_CONFIGS=$([ "$MEM_CONFIGS" == "all" -o -z "${MEM_CONFIGS+x}" -o "$MEM_CONFIGS" == "" ] \
  && echo "dram pmem both" || echo "$MEM_CONFIGS")
MEM_CONFIGS=($MEM_CONFIGS)
NUMA_NODES=`numactl -H | awk '/available:/ {if ($2 > 1) {print "True"} else {print "False"}}'`
if [ $NUMA_NODES == "False" ]; then
  MEM_CONFIGS="dram"
fi

DRAM_NODE=$([ -z "${DRAM_NODE+x}" -o "$DRAM_NODE" == "" ] \
  && echo "0" || echo "$DRAM_NODE")
PMEM_NODE=$([ -z "${PMEM_NODE+x}" -o "$PMEM_NODE" == "" ] \
  && echo "2" || echo "$PMEM_NODE")

REGEX_NUM='^[0-9]+$'
TOTAL_RUNS=$([[ -v TOTAL_RUNS && $TOTAL_RUNS =~ $REGEX_NUM ]] && echo "$TOTAL_RUNS" || echo "1")

KEEP_LOGS=$([ -v KEEP_LOGS -o -z KEEP_LOGS ] && echo "true" || echo "false")
CONTEXT=$([ -v CONTEXT -o -z CONTEXT ] && echo "true" || echo "false")
EXECUTE_BENCHMARKS=$([ -v EXECUTE_BENCHMARKS -o -z EXECUTE_BENCHMARKS ] && echo "true" || echo "false")
PROCESS=$([ -v PROCESS -o -z PROCESS ] && echo "true" || echo "false")
OUTPUT_FILE=$([ -v OUTPUT_FILE ] && echo "$OUTPUT_FILE" || echo "results.txt")
OUTPUT_PATH=`pwd`/results/${OUTPUT_FILE}

declare -a TAIL_TYPES=("Queue" "Service" "Sojourn")
declare -a YCSB_TYPES=("INSERT" "READ" "UPDATE" "READ-MODIFY-WRITE")
declare -a MEMTIER_TYPES=("Sets" "Gets" "Totals")

# NOTE: MEMTIER_METRICS are their indices!
declare -a TAIL_METRICS=("50th" "75th" "90th" "95th" "99th" "99.9th" "99.99th" "Max" "Mean")
declare -a YCSB_METRICS=("50th" "75th" "90th" "95th" "99th" "99.9Per" "99.99Per" "MaxLatency" "AverageLatency")
declare -a MEMTIER_METRICS=("6" "7" "8" "9" "10" "11" "12" "13" "6")




####################################
#            Benchmarks            #
####################################
if [ "$EXECUTE_BENCHMARKS" == "true" ]; then
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
          echo "=========================="
          echo "=        ${TAIL_BENCHMARK}         ="
          echo "=========================="
          echo ""

          cd $TAIL_BENCHMARK

          for MEM_CONFIG in "${MEM_CONFIGS[@]}"; do
            CPU_NODE=$([ "$MEM_CONFIG" == "dram" ] && echo "0" || echo "1")
            MEM_NODE=$([ "$MEM_CONFIG" == "dram" ] && echo "0" || ([ "$MEM_CONFIG" == "pmem" ] && echo "3" || echo "1,3"))
            for TAIL_CONFIG in "${TAIL_CONFIGS[@]}"; do
              for RUN in $(eval echo {1..$TOTAL_RUNS}); do
                echo "${TAIL_CONFIG} - ${MEM_CONFIG} - ${RUN}:"
                echo "-------------------"
                sudo pcm --external_program sudo pcm-memory --external_program \
                  sudo numactl --cpunodebind=${CPU_NODE} --membind=${MEM_NODE} \
                  ./run_${TAIL_CONFIG}.sh \
                  > ../../results/${BENCHMARK}/${TAIL_BENCHMARK}/${MEM_CONFIG}_${TAIL_CONFIG}_${RUN}.txt
                if [ -f "lats.bin" ];
                then
                  python3 ../utilities/parselats.py lats.bin \
                    > ../../results/${BENCHMARK}/${TAIL_BENCHMARK}/lats_${MEM_CONFIG}_${TAIL_CONFIG}_${RUN}.txt
                  rm lats.bin
                fi
                echo ""
              done # End of run
            done # End of tail config (integrated vs networked run)
          done # End of mem config (dram, pmem, etc.)
          cd ..
          echo ""; echo ""
        done # End of tailbench benchmarks
        ;;


      ycsb)
        for YCSB_BENCHMARK in "${YCSB_BENCHMARKS[@]}"; do
          echo "=============================="
          echo "=        Workload-${YCSB_BENCHMARK}         ="
          echo "=============================="
          echo ""

          for MEM_CONFIG in "${MEM_CONFIGS[@]}"; do

            CPU_NODE=$([ "$MEM_CONFIG" == "dram" ] && echo "0" || echo "1")
            MEM_NODE=$([ "$MEM_CONFIG" == "dram" ] && echo "0" || ([ "$MEM_CONFIG" == "pmem" ] && echo "3" || echo "1,3"))
            for RUN in $(eval echo {1..$TOTAL_RUNS}); do
              sudo numactl --cpunodebind=${CPU_NODE} --membind=${MEM_NODE} ${REDIS_DIR}/redis-server & sleep 4
              for YCSB_CONFIG in "${YCSB_CONFIGS[@]}"; do
                echo "${YCSB_CONFIG} - ${MEM_CONFIG} - ${RUN}:"
                echo "-------------------"
                sudo pcm --external_program sudo pcm-memory --external_program \
                  sudo numactl --cpunodebind=${CPU_NODE} --membind=${MEM_NODE} \
                  bin/ycsb ${YCSB_CONFIG} redis -s -P workloads/workload${YCSB_BENCHMARK} -p "redis.host=127.0.0.1" -P config.dat \
                  > ../results/${BENCHMARK}/${YCSB_BENCHMARK}/${MEM_CONFIG}_${YCSB_CONFIG}_${RUN}.txt
                  echo ""
              done # End of YCSB config (run or load)
              ${REDIS_DIR}/redis-cli FLUSHALL
              sudo pkill redis-server & sleep 4
            done # End of run
          done # End of mem config (dram, pmem, etc.)
          echo ""; echo ""
        done # End of YCSB benchmark (ex. workloada)
        ;;


      memtier)
        echo "=============================="
        echo "=      General Memtier       ="
        echo "=============================="
        echo ""

        for MEM_CONFIG in "${MEM_CONFIGS[@]}"; do
          CPU_NODE=$([ "$MEM_CONFIG" == "dram" ] && echo "0" || echo "1")
          MEM_NODE=$([ "$MEM_CONFIG" == "dram" ] && echo "0" || ([ "$MEM_CONFIG" == "pmem" ] && echo "3" || echo "1,3"))
          for RUN in $(eval echo {1..$TOTAL_RUNS}); do
            sudo numactl --cpunodebind=${CPU_NODE} --membind=${MEM_NODE} ${REDIS_DIR}/redis-server & sleep 4
            echo "${MEM_CONFIG} - ${RUN}:"
            echo "-------------------"
            sudo pcm --external_program sudo pcm-memory --external_program \
              sudo numactl --cpunodebind=${CPU_NODE} --membind=${MEM_NODE} \
              memtier_benchmark --pipeline=11 -c 20 -t 1 -d 500 --key-maximum=75000000 --key-pattern=G:G \
              --ratio=1:1 --distinct-client-seed --randomize --test-time=120 --run-count=1 \
              --key-stddev=5125000 --print-percentiles 50,75,90,95,99,99.9,99.99,100 \
              > ../results/${BENCHMARK}/${MEM_CONFIG}_${RUN}.txt
            ${REDIS_DIR}/redis-cli FLUSHALL
            sudo pkill redis-server & sleep 4
            echo ""
          done # End of run
          echo ""; echo ""
        done # End of mem config (dram, pmem, etc.)
        ;;


      *)
        echo "Unrecognized Benchmark"
        ;;
    esac
    cd ..
    echo ""; echo ""; echo ""
  done # End of benchmark suites
fi



####################################
#            Processing            #
####################################

# General helper for parsing pcm data
# $1 = Sample log file for checking existence of logs
# $2 = Wildcard log files for averaging results across runs
# $3 = MEM_CONFIG
general_pcm_parsing() {
  PCM_MEM_CONFIG_SEARCH=$([ "$3" == "dram" ] && echo "DRAM" || ([ "$3" == "pmem" ] && echo "PMM" || echo "System"))
  THROUGHPUT_INDEX=$([ "$PCM_MEM_CONFIG_SEARCH" == "System" ] && echo "5" || echo "6")

  if [ -f "$1" ]; then
    if [ "$CONTEXT" == "true" ]; then
      echo "[OVERALL] LLCRDMISSLAT(ns): " \
        `awk '/LLCRDMISSLAT / {getline; getline; '"$4"' sum += $11; n++} END \
        {if (n > 0) {print sum / n} else {print "Null"}}' $2`

      echo "[OVERALL] ${PCM_MEM_CONFIG_SEARCH} Read Throughput(MB/s): "\
        `awk '/'"$PCM_MEM_CONFIG_SEARCH"' Read Throughput/ {sum += $'"$THROUGHPUT_INDEX"'; n++} END \
        {if (n > 0) print sum / n}' $2`

      echo "[OVERALL] ${PCM_MEM_CONFIG_SEARCH} Write Throughput(MB/s): "\
        `awk '/'"$PCM_MEM_CONFIG_SEARCH"' Write Throughput/ {sum += $'"$THROUGHPUT_INDEX"'; n++} END \
        {if (n > 0) {print sum / n} else {print "Null"}}' $2`

      echo "[OVERALL] DIMM Energy(J): " \
        `awk '/LLCRDMISSLAT / {getline; getline; sum += $10; n++} END \
        {if (n > 0) {print sum / n} else {print "Null"}}' $2`


    else
      echo "Overall:"
      echo `awk '/LLCRDMISSLAT / {getline; getline; '"$4"' sum += $11; n++} END \
        { if (n > 0) {print sum / n;} else {print "Null"} }' $2`

      echo `awk '/'"$PCM_MEM_CONFIG_SEARCH"' Read Throughput/ {sum += $'"$THROUGHPUT_INDEX"'; n++} END \
        { if (n > 0) {print sum / n;} else {print "Null"} }' $2`

      echo `awk '/'"$PCM_MEM_CONFIG_SEARCH"' Write Throughput/ {sum += $'"$THROUGHPUT_INDEX"'; n++} END \
        { if (n > 0) {print sum / n;} else {print "Null"} }' $2`

      echo `awk '/DIMM energy / {getline; getline; sum += $10; n++} END \
        { if (n > 0) {print sum / n;} else {print "Null"} }' $2`
    fi
  fi
}



if [ "$PROCESS" == "true" ]; then
 echo "Porcessing..."
  {
    cd results
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
            echo "============================"
            echo "=        ${TAIL_BENCHMARK}         ="
            echo "============================"
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
                    if [ -f "lats_${MEM_CONFIG}_${TAIL_CONFIG}_1.txt" ]; then
                      if [ "$CONTEXT" == "true" ]; then
                        echo "[$TAIL_TYPE] $TAIL_METRIC: " \
                          `awk '/\['"$TAIL_TYPE"'\] '"$TAIL_METRIC"'/ {sum += $5; n++} END \
                          { if (n > 0) {print sum / n; print "ms"} else {print "Null"} }' \
                          lats_${MEM_CONFIG}_${TAIL_CONFIG}_*.txt`
                      else
                        echo `awk '/\['"$TAIL_TYPE"'\] '"$TAIL_METRIC"'/ {sum += $5; n++} END \
                          { if (n > 0) {print sum / n} else {print "Null"}}' \
                          lats_${MEM_CONFIG}_${TAIL_CONFIG}_*.txt`
                      fi
                    else
                      echo "Log file not found (failed test?)"
                      break
                    fi
                  done
                echo ""
                done
                SOCKET_PCM=$([ "$MEM_CONFIG" == "dram" ] && echo "" || echo "getline;")
                SAMPLE_PCM_FILE=${MEM_CONFIG}_${TAIL_CONFIG}_1.txt
                PCM_FILES=${MEM_CONFIG}_${TAIL_CONFIG}_*.txt
                general_pcm_parsing "${SAMPLE_PCM_FILE}" "${PCM_FILES}" "${MEM_CONFIG}" "${SOCKET_PCM}"
                echo ""
              done
              echo ""; echo "";
            done
            cd ..
          done
          ;;


        ycsb)
          for YCSB_BENCHMARK in "${YCSB_BENCHMARKS[@]}"; do
            echo "============================="
            echo "=        Workload ${YCSB_BENCHMARK}         ="
            echo "============================="
            echo ""
            cd ${YCSB_BENCHMARK}

            for MEM_CONFIG in "${MEM_CONFIGS[@]}"; do
              for YCSB_CONFIG in "${YCSB_CONFIGS[@]}"; do
                echo "$MEM_CONFIG - $YCSB_CONFIG:"
                echo "============"

                # Metrics for tail latency reported by ycsb
                #############################################
                for YCSB_TYPE in "${YCSB_TYPES[@]}"; do
                 if [ "$CONTEXT" == "false" ]; then
                    echo "$YCSB_TYPE:"
                  fi
                  for YCSB_METRIC in "${YCSB_METRICS[@]}"; do
                    if [ -f "${MEM_CONFIG}_${YCSB_CONFIG}_1.txt" ]; then
                      if [ "$CONTEXT" == "true" ]; then
                        echo "[$YCSB_TYPE] $YCSB_METRIC (ms): " \
                          `awk '/\['"$YCSB_TYPE"'\], '"$YCSB_METRIC"'/ {sum += $3; n++} END \
                          {if (n > 0) {print sum / n} else {print "Null"}}' \
                          ${MEM_CONFIG}_${YCSB_CONFIG}_*.txt`
                      else
                        echo `awk '/\['"$YCSB_TYPE"'\], '"$YCSB_METRIC"'/ {sum += $3; n++} END \
                          {if (n > 0) {print sum / n} else {print "Null"}}' \
                          ${MEM_CONFIG}_${YCSB_CONFIG}_*.txt`
                      fi
                    fi
                  done
                  echo ""
                done
                SOCKET_PCM=$([ "$MEM_CONFIG" == "dram" ] && echo "" || echo "getline;")
                SAMPLE_PCM_FILE=${MEM_CONFIG}_${YCSB_CONFIG}_1.txt
                PCM_FILES=${MEM_CONFIG}_${YCSB_CONFIG}_*.txt
                general_pcm_parsing "${SAMPLE_PCM_FILE}" "${PCM_FILES}" "${MEM_CONFIG}"  "${SOCKET_PCM}"
                echo ""
              done
              echo ""; echo "";
            done
            cd ..
          done
          ;;


        memtier)
          echo "=========================="
          echo "=    GENERAL MEMTIER     ="
          echo "=========================="
          echo ""

          for MEM_CONFIG in "${MEM_CONFIGS[@]}"; do
            echo "$MEM_CONFIG:"
            echo "--------------"
            for MEMTIER_TYPE in "${MEMTIER_TYPES[@]}"; do
              echo "$MEMTIER_TYPE:"
              for MEMTIER_METRIC in "${MEMTIER_METRICS[@]}"; do
                if [ -f "${MEM_CONFIG}_1.txt" ]; then
                  echo `awk '/'"$MEMTIER_TYPES"'/ {sum += $'"$MEMTIER_METRIC"'; n++} END \
                    {if (n > 0) {print sum / n} else {print "Null"}}' \
                    ${MEM_CONFIG}_*.txt`
                fi
              done
              echo ""

            done
            SOCKET_PCM=$([ "$MEM_CONFIG" == "dram" ] && echo "" || echo "getline;")
            SAMPLE_PCM_FILE=${MEM_CONFIG}_1.txt
            PCM_FILES=${MEM_CONFIG}_*.txt
            general_pcm_parsing "${SAMPLE_PCM_FILE}" "${PCM_FILES}" "${MEM_CONFIG}"  "${SOCKET_PCM}"
            echo ""; echo ""; echo ""
          done
          ;;


        *)
          echo "Unrecognized Benchmrk"
          ;;
      esac
      cd ..
    done

    # if [ "$KEEP_LOGS" == "false" ]; then
    #   rm *_lats_*.txt
    # fi
    cd ..
  } > ${OUTPUT_PATH}
fi
