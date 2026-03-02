#!/usr/bin/env bash

echo -e "\n========================================================"
echo "Starting Ray Serve..."
echo "-> Inference Endpoint will be at: http://127.0.0.1:8000"
echo "-> Ray Dashboard will be at:      http://127.0.0.1:8265"
echo -e "========================================================\n"

# serve run serve_bert:app
serve run serve_bert_pydantic:deployment

# by default, Serve will expose http endpoint on port 8000, but you can change it with the --port flag
# serve run serve_bert:app --port 9000
# Ray Dashboard: http://localhost:8265
