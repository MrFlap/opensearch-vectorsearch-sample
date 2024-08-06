import argparse

parser = argparse.ArgumentParser(
    prog='knn-benchmark',
    description=
    """
    A program that runs a sequence of knn operations and log metrics.
    Specifically designed to test vector streaming metrics.
    """
)
parser.add_argument('-s', '--stream_limit', type=str, default='default', help='Maximum size of vector batch streamed to index')
args = parser.parse_args()

filenames = {
    'sift': 'sift-128-euclidean.hdf5',
    'gist': 'gist-960-euclidean.hdf5'
}

from opensearchpy import OpenSearch, RequestsHttpConnection
import os


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

if args.stream_limit != 'default':
    settings = {
        "persistent": {
            "knn.vector_streaming_memory.limit": args.stream_limit
        },
        "transient": {
            "cluster.routing.allocation.disk.watermark.low": "92%",
            "cluster.routing.allocation.disk.watermark.high": "95%",
            "cluster.routing.allocation.disk.watermark.flood_stage": "98%",
            "cluster.info.update.interval": "1m"
        }
    }
    client.cluster.put_settings(body=settings)