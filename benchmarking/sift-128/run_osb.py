from time import sleep
import docker
import os

# Create a Docker client
client = docker.from_env()

# Set the path to the container image
# image_path = "your_docker_image_name:tag"
image_path = "constraint-env-bench:memory-fix"

for dataset in ["sift"]:
    for stream_limit in ["default", "1mb", "10mb", "100mb"]:
        # Create a new container for each iteration
        container = client.containers.run(
            image_path,
            mem_limit="2.5g",
            cpuset_cpus="4",
            ports={
                "9200": "9200"
            }
        )
        container_id = container.id

        print(f"Running k-nn benchmark for dataset {dataset} with streaming limit {stream_limit} on container {container_id} for process 79!")

        # Copy the Python script to the container
        with open("/home/ec2-user/opensearch-vectorsearch-sample/pidmem.tar.gz", "rb") as f:
            container.put_archive("/home/ci-runner/", f.read())

        # Install the required packages
        container.exec_run("pip install matplotlib psutil")

        processes = container.exec_run("ps -ef")
        jpid = [line.split()[1] for line in processes.output.decode().split("\n") if "java" in line][0]
        # Run the Python script in the container
        container.exec_run(f"python3 /home/ci-runner/pidmem.py {jpid} -j -g 'graph_{dataset}_{stream_limit}.png' -r > 'test_{dataset}_{stream_limit}.json'")

        # Get the process IDs running the Python script
        processes = container.exec_run("ps -ef")
        dpids = [line.split()[1] for line in processes.output.decode().split("\n") if "python3" in line]
        print(dpids)

        os.system(f"python3 /home/ec2-user/opensearch-vectorsearch-sample/benchmarking/sift-128/set-limit.py -s {stream_limit}")

        # Run the osb
        os.system(f"/home/ec2-user/opensearch-benchmark-workloads/vectorsearch/run_bench.sh test_${stream_limit}_osb.md")

        print("Done executing benchmark!")
        print("Generating log data!")

        # Kill the Docker memory tracker
        for dpid in dpids:
            container.exec_run(f"kill -s 15 {dpid}")

        print("Done!")

        # Stop and remove the container
        container.stop()
        container.remove()