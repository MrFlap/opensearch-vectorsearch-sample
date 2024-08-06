docker cp ~/opensearch-vectorsearch-sample/pidmem.py $1:/home/ci-runner/
docker exec $1 sh -c "pip install matplotlib psutil"

JPROCESSES=$(docker exec -it $1 sh -c "ps -ef")
JPID=$(echo "$JPROCESSES" | grep -E 'python3' | awk '{print $2}')

for dataset in sift; do
    for stream_limit in 1mb 10mb 100mb; do
        echo "Running k-nn benchmark for dataset ${dataset} with streaming limit $stream_limit on container $1 for process $JPID!"
        docker exec $1 sh -c "python3 /home/ci-runner/pidmem.py $JPID -j -g 'graph_${dataset}_${stream_limit}_prev.png' -r > 'test_${dataset}_${stream_limit}_prev.json'" &
        PROCESSES=$(docker exec -it $1 sh -c "ps -ef")
        DPIDS=$(echo "$PROCESSES" | grep -E 'python3' | awk '{print $2}')
        echo $DPIDS
        python3 knn-benchmark.py -s $stream_limit -d $dataset > test_${dataset}_${stream_limit}_prev.txt
        echo "Done executing benchmark!"
        echo "Generating log data!"
        # Kill docker memory tracker
        for DPID in $DPIDS; do
            #echo $DPID
            docker exec $1 sh -c "(kill -s 15 $DPID) && (echo 'KILLED ${DPID}')"
        done
        echo "Done!"
    done
done