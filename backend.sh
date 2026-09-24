#!/bin/bash

echo "Starting Backend Server"
uv run uvicorn main:app --reload