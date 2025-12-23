#!/usr/bin/env bash
set -e

# Start Flask backend in background and log output
python3 server.py &> server.log &

# Give backend a moment to start
sleep 2

# Start Streamlit app
streamlit run app.py --server.port 8501 --server.address 0.0.0.0 --server.enableCORS false
