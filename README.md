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


## Setup
Run the setup script to auto-install dependencies and setup benchmarks:
`$ ./setup.sh`

## Running a Test
Options when running:
- -r - number of runs per test to average
- -b - benchmark suites to run ('all' - default, 'tailbench', 'ycsb', or 'memtier')
- -e - Execute the benchmarks and place log files in memsys-benchmarking/results/...
- -p - Process the log files in memsys-benchmarking/results/...

Example: run five times per benchmark (averaging out results), execute only the tailbench and ycsb benchmarks, and process the resulting logs:
`$ ./run.sh -r 5 -b "tailbench ycsb" -e -p`
