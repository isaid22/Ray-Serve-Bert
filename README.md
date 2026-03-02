# Ray-Serve-Bert
This repo contains example and explanation for setting up Ray Serve in Nvidia RTX4060 GPU.

To run this example, there needs to be two terminals, one for server, one for client.

## Server terminal

Run server:

```
./run_ray_local.sh
```

## Client terminal:

Run single client with single observation or input:

```
./single-client.sh
```

Alternatively, run batch observations:

```
./batch-client.sh
```

Output will be embedding returned by the BERT base model.

## Ray application

ONce Ray Server is started, there willbe these informations shown:

```
========================================================
Starting Ray Serve...
-> Inference Endpoint will be at: http://127.0.0.1:8000
-> Ray Dashboard will be at:      http://127.0.0.1:8265
========================================================
```

Ray Dashboard will be available for monitoring the GPU node and application performance.


