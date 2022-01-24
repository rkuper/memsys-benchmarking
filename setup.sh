#!/bin/bash
# Main setup script for all benchmarks

declare -a BENCHMARKS=("tailbench" "ycsb" "memtier")
declare -a TAIL_BENCHMARKS=("harness" "img-dnn" "masstree" "moses" "silo" "specjbb" "sphinx" "xapian")

sudo apt install -y htop numatop ipmctl ndctl openjdk-8-jdk

for BENCHMARK in "${BENCHMARKS[@]}"; do
  if [ ! -d "${BENCHMARK}" ]; then
    mkdir results/${BENCHMARK}
    case $BENCHMARK in
      tailbench)
        # Clone and make base files
        git clone https://github.com/rkuper/tailbench.git ${BENCHMARK}; cd ${BENCHMARK}
        mkdir scratch

        # General tools
        sudo apt install -y sysstat g++ subversion automake libtool python-dev python2.7-dev make cmake

        # Tools for each specific benchmark
        sudo apt install -y zlib1g-dev libopencv-dev libboost-dev swift libicu-dev libboost-all-dev libbz2-dev \
                            liblzma-dev graphviz imagemagick libgoogle-perftools-dev ant uuid-dev \
                            libjemalloc-dev libnuma-dev libdb-dev libdb++-dev libaio-dev libssl-dev swig bison \
                            libreadline-dev libgtop2-dev libncurses-dev libpulse-dev libxapian-dev

        # Build each individual test
        if [ "`command -v gcc-5`" == "" ]; then
          if [ "`sudo grep 'deb http://dk.archive.ubuntu.com/ubuntu/ xenial main' /etc/apt/sources.list`" == "" ]; then
            echo "deb http://dk.archive.ubuntu.com/ubuntu/ bionic main" | sudo tee -a /etc/apt/sources.list
            echo "deb http://dk.archive.ubuntu.com/ubuntu/ bionic universe" | sudo tee -a /etc/apt/sources.list
            sudo apt update
            sudo apt install -y gcc-5 g++-5 g++-5-multilib
          fi
          sudo update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-5 40 --slave /usr/bin/g++ g++ /usr/bin/g++-5
          sudo update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-9 60 --slave /usr/bin/g++ g++ /usr/bin/g++-9
        fi
        `sudo update-alternatives --config gcc <<< '1'; echo ""`
        for TAIL_BENCHMARK in "${TAIL_BENCHMARKS[@]}"; do
          cd $TAIL_BENCHMARK; sudo ./build.sh; cd ..
          if [ "$TAIL_BENCHMARK" != "harness" ]; then
            mkdir ../results/${BENCHMARK}/${TAIL_BENCHMARK}
          fi
        done
        `sudo update-alternatives --config gcc <<< '0'; echo ""`

        # Grab the datasets
        # wget http://tailbench.csail.mit.edu/tailbench.inputs.tgz -O data.tgz
        # tar zxf data.tgz; mv tailbench.inputs data
        # rm -f data.tgz
        cd ..
        ;;



      ycsb)
        # Clone
        git clone https://github.com/brianfrankcooper/YCSB.git ${BENCHMARK}

        # Dependencies
        sudo apt install -y redis memcached libmemcached-dev
        ;;



      memtier)
        # Clone
        git clone https://github.com/RedisLabs/memtier_benchmark.git ${BENCHMARK}; cd ${BENCHMARK}

        # Dependencies
        sudo apt install -y build-essential autoconf automake libpcre3-dev libevent-dev pkg-config zlib1g-dev

        # Build
        cd ${BENCHMARK}
        autoreconf -ivf; ./configure
        make; sudo make install
        cd ..
        ;;

      *)
        echo "[ERROR] Could not find benchmark: ${BENCHMARK}"
        break
        ;;
    esac
  fi
done



# Build tools for measuring performance counters
if [ "`command -v pcm`" == "" ]; then
  git clone https://github.com/opcm/pcm.git; cd pcm
  mkdir build; cd build
  cmake ..
  cmake --build . --parallel
fi
