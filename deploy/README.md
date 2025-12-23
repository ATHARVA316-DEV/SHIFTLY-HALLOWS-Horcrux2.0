Deployment with Docker

This folder contains instructions and basic configuration to run the app in Docker.

Build image (from repo root):

```bash
docker build -t shiftly-horcrux:latest .
```

Run container (map ports 8501 for Streamlit and 9999 for Flask):

```bash
docker run --rm -p 8501:8501 -p 9999:9999 shiftly-horcrux:latest
```

Notes and limitations:

- The project performs camera capture and displays GUI windows (`cv2.imshow`) in `server.py`. In a headless container these windows will not appear; consider removing or guarding `cv2.imshow` calls when running in Docker.
- ONNX and OpenCV can be heavy; builds may take a while.
- To deploy a live site on the web use a container host (Render, Railway, Fly.io, or a VPS). Connect this GitHub repo to the host for automated deploys from the `deploy/docker` branch.

Pushing the `deploy/docker` branch (local):

```bash
git checkout -b deploy/docker
git add Dockerfile start.sh requirements.txt .dockerignore deploy/README.md
git commit -m "Add Dockerfile, start script and deployment README"
git push -u origin deploy/docker
```

If `git push` fails due to lack of permissions, create a personal access token or configure SSH and run the `git push` command again.
