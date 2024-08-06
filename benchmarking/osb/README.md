# OSB Benchmaring
This folder contains the methods to run OSB benchmarks and get metrics.

To run, first create a docker image from opensearch-cluster-setups.

Once it's finished compiling, execute ./run_bench.sh {IMAGE TAG} {FILENAME TAG} for SIFT dataset

The filename tag is whatever extra tags you want to add.

You can also execute ./run_bench_768.sh {IMAGE TAG} {FILENAME TAG} for 768D dataset

The run_bench files are not meant to be executed alone.