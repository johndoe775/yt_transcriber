# Python Snap Backend

Run the API from this directory:

```bash
uvicorn yt_mcp.api:app --app-dir src --host 0.0.0.0 --port 8000
```

## Deploy on SnapDeploy

Connect this repository in SnapDeploy and deploy it as a Docker container. The
root-level `Dockerfile` builds the API and listens on the platform-provided
`PORT` (falling back to `8000` for local runs). After deployment, check
`/health` on the generated URL.

- `GET /health` reports server and Argos model availability.
- `GET /transcript?url=<youtube-url>&source_language=auto` returns transcript text, segments, and paragraphs.
- `GET /translate?url=<youtube-url>&source_language=auto&target_language=en` returns the transcript and its translation.

Install the Argos language packages needed by your deployment before starting
the server. Translation does not download models at runtime.
