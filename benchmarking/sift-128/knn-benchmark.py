import argparse

parser = argparse.ArgumentParser(
    prog='knn-benchmark',
    description=
    """
    A program that runs a sequence of knn operations and log metrics.
    Specifically designed to test vector streaming metrics.
    """
)
parser.add_argument('-s', '--stream_limit', type=str, default='1mb', help='Maximum size of vector batch streamed to index')
parser.add_argument('-i', '--index_type', type=str, default='hnsw', help='Type of knn index to use')
parser.add_argument('-d', '--dataset', type=str, default='sift', help='Dataset file to use')
args = parser.parse_args()

filenames = {
    'sift': 'sift-128-euclidean.hdf5',
    'gist': 'gist-960-euclidean.hdf5'
}

# Read Data set
import numpy as np
import h5py
from dotenv import load_dotenv
from opensearchpy import OpenSearch, RequestsHttpConnection
import os
import time
from tqdm import tqdm
from opensearchpy.helpers import bulk

dataset = h5py.File(filenames[args.dataset], "r")
X_TRAIN = np.array(dataset["train"])
X_TEST = np.array(dataset["test"])
X_NEIGHBORS = np.array(dataset["neighbors"])
dimension = int(dataset.attrs["dimension"]) if "dimension" in dataset.attrs else len(X_TRAIN[0])

print(f"Ingest dataset size is : {len(X_TRAIN)}")
print(f"Queries dataset size is : {len(X_TEST)}")
print(f"dataset dimensions is : {dimension}")

res = load_dotenv("environment.txt")

#OS_HOST = os.getenv('OS_HOST')
OS_HOST = "172.17.0.2"
#OS_PORT = os.getenv('OS_PORT')
OS_PORT = "9200"
OS_USER = os.getenv('USER_NAME')
OS_PASSWORD = os.getenv('PASSWORD')
vector_index_name = os.getenv('VECTOR_INDEX_NAME', "test-vector")


client = OpenSearch(
    hosts = [{'host': OS_HOST, 'port': OS_PORT}],
    http_compress = True, # enables gzip compression for request bodies
    http_auth = (OS_USER, OS_PASSWORD),
    use_ssl = False,
    verify_certs = True,
    connection_class = RequestsHttpConnection,
    timeout=6000,
    pool_maxsize = 20
)

client.info()

print(f"vector index name from env is : {vector_index_name}")

def create_index(index_name):
    index_mappings = {
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0,
            "index": {
                "knn": True,
                "knn.algo_param.ef_search": 128, # Adjust to improve precision. Higher improves recall & precsion but increases latency. Lower degrades recall & precision but improves latency.
                "refresh_interval" : "-1", # This is to ensure that we are creating mininal number of segments.
            },
        },
        "mappings": {
            "properties": {
                "vec": {
                    "type": "knn_vector",
                    "dimension": dimension,
                    "index": "true",
                    "method": {
                        "name": args.index_type,
                        "space_type": "l2", # l2 for SIFT, cosinesimil for typical
                        "engine": "faiss",
                        "parameters": {
                            "ef_construction": 128
                        }
                    }
                }
            }
        }
    }

    if client.indices.exists(index=index_name):
        response = client.indices.delete(index=index_name)
        print(f"Deleting the index. Response : {response}")

    response = client.indices.create(index=index_name, body=index_mappings)
    print(f"Creating the index. Response : {response}")

# ingest data in the index

create_index(vector_index_name)

bulk_size = 1000
def dataGen():
    for i, vec in enumerate(X_TRAIN):
        yield { "_index": vector_index_name, "_id": str(i), "vec": vec.tolist() }

settings = {
    "persistent": {
        "knn.vector_streaming_memory.limit": args.stream_limit
    }
}
client.cluster.put_settings(body=settings)

data_to_ingest = []
total_time_to_ingest = 0.
ingest_latency = []
mem_usage = []
for data in tqdm(dataGen(), total=len(X_TRAIN)):
    if len(data_to_ingest) == bulk_size:
        start = time.time()
        (res, errors) = bulk(client, data_to_ingest)
        end = time.time()
        total_time_to_ingest += (end-start)
        ingest_latency.append(end-start)
        if len(errors) != 0:
            print(errors)
            data_to_ingest = []
            StopIteration
        else:
            data_to_ingest = []

    if len(data_to_ingest) < bulk_size:
        data_to_ingest.append(data)
    
    #print(client.cluster.health())
    

if len(data_to_ingest) != 0:
    start = time.time()
    (_, errors) = bulk(client, data_to_ingest)
    mem_usage += client.cluster.health(index=[vector_index_name])
    end = time.time()
    total_time_to_ingest += (end-start)
    if len(errors) != 0:
        print(errors)
    else:
        data_to_ingest = []

print(f"Ingestion completed. Total time to ingest = {total_time_to_ingest} seconds, average time per document: {total_time_to_ingest/(len(X_TRAIN))}")
print(mem_usage)
print(client.cat.indices(index=vector_index_name, params={'format': 'csv', 'v': 'true'}))

# Refresh the index as we set the refresh interval to -1
client.indices.refresh(index=vector_index_name)

client.indices.forcemerge(index=vector_index_name, max_num_segments=1)

client.indices.refresh(index=vector_index_name)

# Check index details, you should see 1M documents in the index.
print(client.cat.indices(index=vector_index_name))

print("Segments Info After refresh...")

segments = client.cat.segments(vector_index_name, params={"format": "json"})

print(f"Total segments are: {len(segments)}")

print(f"Printing Segment info : \n{client.cat.segments(index=vector_index_name, params={'format': 'csv', 'v': 'true'})}")

def searchQueryGen(input_array=X_TEST, k=100):
    for i, vec in enumerate(input_array):
        yield {
            "_source": False, # Don't get the source as this impacts latency
            "size": k,
            "query": {
                "knn": {
                    "vec": {
                        "vector": vec.tolist(),
                        "k": k
                    }
                }
            }
        }


neighbors_lists = []
search_latency = []
took_time = []
k = 10
for query in tqdm(searchQueryGen(input_array=X_TEST, k=k), total=len(X_TEST)):
    start = time.time()
    search_response = client.search(body=query, index=vector_index_name, _source=False, docvalue_fields=["_id"], stored_fields="_none_")
    end = time.time()
    search_latency.append(end - start)
    took_time.append(search_response["took"])
    search_hits = search_response['hits']['hits']
    search_neighbors = [int(hit["fields"]["_id"][0]) for hit in search_hits]
    neighbors_lists.append(search_neighbors)

print("Calculating Recall ...")
query_number:int = 0
recall:float = 0.
for actual_neighbors in tqdm(neighbors_lists):
    expected_neighbors = X_NEIGHBORS[query_number][0:k]
    counter = 0.0
    query_number = query_number + 1
    for element in actual_neighbors:
        if element in expected_neighbors:
            counter = counter + 1
    recall = recall + (counter/k)

recall = recall / len(X_TEST)

print(f'Recall @k{k} is : {recall}')

response = client.indices.delete(index=vector_index_name)
print(f"Deleting the index. Response : {response}")

print("========================== Search Metrics ===================================")
print("========================== Server Side Latency ===================================")
print(f"average took_time(ms): {np.average(took_time)}") 
print(f"p50 took_time(ms): {np.percentile(took_time, 50)}") 
print(f"p90 took_time(ms): {np.percentile(took_time, 90)}")
print(f"p99 took_time(ms): {np.percentile(took_time, 99)}")


print("\n\n========================== Client side latency ===================================")
print(f"average Latency(ms): {np.average(search_latency) *1000}") 
print(f"p50 Latency(ms): {np.percentile(search_latency, 50) *1000}") 
print(f"p90 Latency(ms): {np.percentile(search_latency, 90) *1000}")
print(f"p99 Latency(ms): {np.percentile(search_latency, 99) *1000}")

print("\n\n========================== Recall Metrics===================================")
print(f'Recall @k{k} is : {recall}')