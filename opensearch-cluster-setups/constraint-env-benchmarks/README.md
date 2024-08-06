## Build the image
Ensure that the Dockerfile are in the directory.

### Memory Fix Version
```
docker build -f Dockerfile_Memory_Fix -t constraint-env-bench:memory-fix .
```

### No Memory Fix Version
```
docker build -f Dockerfile_No_Memory_Fix -t constraint-env-bench:no-memory-fix .
```

### 2.14 Version
```
docker build -f Dockerfile_2_14 -t constraint-env-bench:2-14 .
```

### 2.13 Version
```
docker build -f Dockerfile_2_13 -t constraint-env-bench:2-13 .
```

## Running the image
### 2.13 and 2.14
```
docker run -d -it -m 3g --cpus 4 -p 0.0.0.0:9200:9200 <IMAGE-NAME>
```

### Memory Fix
```
docker run -d -it -m 2.5g --cpus 4 -p 0.0.0.0:9200:9200 <IMAGE-NAME>
```

## SSH in the container
```
docker exec -i -t <ContainerID> bash
```