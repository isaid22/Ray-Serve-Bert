#!/usr/bin/env bash

curl -X POST http://127.0.0.1:8000/ \
  -H "Content-Type: application/json" \
  -d '{"texts":["first sentence","second sentence","third sentence", "fourth sentence"]}'