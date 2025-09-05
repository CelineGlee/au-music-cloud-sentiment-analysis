docker run --rm -v $(pwd):/app -w /app fission/python-builder \
    bash -c "pip install --no-cache-dir -r requirements.txt"

