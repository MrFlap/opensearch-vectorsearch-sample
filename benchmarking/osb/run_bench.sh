export URL=127.17.0.2
export PORT=9200
export PARAMS_FILE=../../opensearch-benchmark-workloads/vectorsearch/params/faiss-sift-128-l2.json
export PROCEDURE=no-train-test

opensearch-benchmark execute-test --target-hosts $URL:$PORT --workload-params ${PARAMS_FILE} --test-procedure=${PROCEDURE} --pipeline benchmark-only --workload vectorsearch --results-file $1 --kill-running-processes
