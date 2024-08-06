EXTRATAGS=$2

for stream_limit in default 1mb 10mb 100mb; do
    docker run -d --name "container_$stream_limit" -it --cpus 4 -p 0.0.0.0:9200:9200 $1
    sleep 1s
    docker cp /home/ec2-user/opensearch-vectorsearch-sample/pidmem.py "container_$stream_limit":/home/ci-runner/
    docker exec "container_$stream_limit" sh -c "pip install matplotlib psutil"
    PROCESSES=$(docker exec -it "container_$stream_limit" sh -c "ps -ef")
    JPID=$(echo "$PROCESSES" | grep -E 'java' | awk '{print $2}')
    docker exec -d "container_$stream_limit" sh -c "python3 /home/ci-runner/pidmem.py $JPID -j -g 'graph_${stream_limit}_osb_${EXTRATAGS}.png' -r > 'test_${stream_limit}_osb_${EXTRATAGS}.json'"
    echo "Running osb benchmark for dataset ${dataset} with streaming limit $stream_limit on container $1 for process $JPID!"
    DPIDS=$(docker exec "container_$stream_limit" sh -c "ps -ef" | grep -E 'python3' | awk '{print $2}')
    echo $DPIDS
    python3 set-limit.py -s $stream_limit
    /bin/bash /home/ec2-user/opensearch-benchmark-workloads/vectorsearch/run_bench_768.sh test_${stream_limit}_osb_${EXTRATAGS}.md
    echo "Done executing benchmark!"
    echo "Generating log data!"
    # Kill docker memory tracker
    for DPID in $DPIDS; do
        #echo $DPID
        docker exec "container_$stream_limit" sh -c "(kill -s 15 $DPID) && (echo 'KILLED ${DPID}')"
    done
    sleep 3m
    docker cp "container_$stream_limit":/home/ci-runner/graph_${stream_limit}_osb_${EXTRATAGS}.png .
    docker cp "container_$stream_limit":/home/ci-runner/test_${stream_limit}_osb_${EXTRATAGS}.json .
    docker stop "container_$stream_limit"
    docker rm "container_$stream_limit"
    echo "Done!"
done