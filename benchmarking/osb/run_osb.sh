#
# ROUGH TOOL TO INITIALIZE DOCKER CONTAINER, RUN BENCHMARKS, GET METRICS, THEN DELETE
# FIRST ARGUMENT IS THE DOCKER IMAGE ID, NEXT ARGUMENT IS AN EXTRA TAGS TO APPEND TO THE FILE
#
# MAKE SURE TO CLEAR PREVIOUS DOCKER INSTANCES BEFORE RUNNING
#
# THIS IS FOR THE SIFT DATASET
#

EXTRATAGS=$2

for stream_limit in default 1mb 10mb 100mb; do
    # Run Docker Container
    docker run -d --name "container_$stream_limit" -it --cpus 4 -p 0.0.0.0:9200:9200 $1

    # Make sure it is initialized
    sleep 1s

    # Get ready to run memory tracker
    docker cp ../../mem_usage_pid/pidmem.py "container_$stream_limit":/home/ci-runner/
    docker exec "container_$stream_limit" sh -c "pip install matplotlib psutil"

    # Get Java PID
    PROCESSES=$(docker exec -it "container_$stream_limit" sh -c "ps -ef")
    JPID=$(echo "$PROCESSES" | grep -E 'java' | awk '{print $2}')

    # Execute the memory tracker
    docker exec -d "container_$stream_limit" sh -c "python3 /home/ci-runner/pidmem.py $JPID -j -g 'graph_${stream_limit}_osb_${EXTRATAGS}.png' -r > 'test_${stream_limit}_osb_${EXTRATAGS}.json'"
    echo "Running osb benchmark for dataset ${dataset} with streaming limit $stream_limit on container $1 for process $JPID!"

    # Get PIDS to delete the memory tracker
    DPIDS=$(docker exec "container_$stream_limit" sh -c "ps -ef" | grep -E 'python3' | awk '{print $2}')
    echo $DPIDS

    # Set the streaming limit
    python3 set-limit.py -s $stream_limit

    # Run the benchmark
    /bin/bash run_bench.sh test_${stream_limit}_osb_${EXTRATAGS}.md
    echo "Done executing benchmark!"
    echo "Generating log data!"

    # Kill docker memory tracker
    for DPID in $DPIDS; do
        docker exec "container_$stream_limit" sh -c "(kill -s 15 $DPID) && (echo 'KILLED ${DPID}')"
    done

    # Give time to generate graph and data
    sleep 30s

    # Copy the data
    docker cp "container_$stream_limit":/home/ci-runner/graph_${stream_limit}_osb_${EXTRATAGS}.png .
    docker cp "container_$stream_limit":/home/ci-runner/test_${stream_limit}_osb_${EXTRATAGS}.json .

    # Kill the container
    docker stop "container_$stream_limit"
    docker rm "container_$stream_limit"
    echo "Done!"
done