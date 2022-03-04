## Included Benchmarks
- Tailbench: 
  - img-dnn      : Image recognition
  - masstree     : Key-value store
  - moses        : Statistical machine translation
  - silo         : OLTP database (in-memory)
  - specjbb      : Java middleware
  - sphinx       : Speech recognition
  - xapian       : Online search
- YCSB (Redis):
  - a - 50/50 reads and writes
  - b - 95/5 reads and writes
  - c - 100% reads
  - d - Read latest workload
  - f - Read-modify-write
- Memtier
- PMBench


## Setup
Run the setup script to auto-install dependencies and setup benchmarks:
`$ ./setup.sh`

## Running a Test
Options when running:
- -s - number of samples (runs) per test to average
- -b - benchmark suites to run: 'all' - default, 'tailbench', 'ycsb', 'memtier', or 'pmbench'
- -l - Local NUMA node: 0 - default
- -r - Remote NUMA node: 1 - default
- -m - Memory configurations for where benchmarks exclusively allocate memory to: 'all' - default if more than 1 NUMA node, 'local' - default if 1 NUMA node, 'remote', 'both')
- -e - Execute the benchmarks and place log files in memsys-benchmarking/results/...
- -p - Process the log files in memsys-benchmarking/results/...

Example: sample five times per benchmark (averaging out results), execute only the tailbench and ycsb benchmarks, local numa node is 0, remote node is 1, run only local and remote memory configurations, and process the resulting logs:
`$ ./run.sh -s 5 -b "tailbench ycsb" -l 0 -r "1" -m "local remote" -e -p`
