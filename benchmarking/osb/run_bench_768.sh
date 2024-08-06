export URL=127.17.0.2
export PORT=9200
export PARAMS_FILE=../../opensearch-benchmark-workloads/vectorsearch/params/corpus/1million/faiss-cohere-768-dp.json
export PROCEDURE=no-train-test

opensearch-benchmark execute-test --target-hosts $URL:$PORT --workload-params ${PARAMS_FILE} --test-procedure=${PROCEDURE} --pipeline benchmark-only --workload vectorsearch --results-file $1 --kill-running-processes
