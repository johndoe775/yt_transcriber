# Python Snap Backend
##
Run the API from this directory:

```bash
uvicorn yt_mcp.api:app --app-dir src --host 0.0.0.0 --port 8000
```

## Deploy on SnapDeploy

Connect this repository in SnapDeploy and deploy it as a Docker container. The
root-level `Dockerfile` builds the API and listens on the platform-provided
`PORT` (falling back to `8000` for local runs). After deployment, check
`/health` on the generated URL.

## GitHub Pages UI

The `Deploy GitHub Pages` workflow publishes the UI on pushes to `main`. Add a
repository Actions secret named `BACKEND_API_URL` containing the public HTTPS
SnapDeploy URL, then set **Settings → Pages → Build and deployment → Source** to
**GitHub Actions**. The workflow inserts that URL into `index.html` before
publishing. The URL is visible in the public page, so do not put credentials in
it. The API allows cross-origin GET requests for the static UI.

- `GET /health` is a lightweight server liveness check.
- `GET /translation-health` reports whether Argos language models are installed.
- `GET /transcript?url=<youtube-url>&source_language=auto` returns transcript text, segments, and paragraphs.
- `GET /translate?url=<youtube-url>&source_language=auto&target_language=en` returns the transcript and its translation.

Install the Argos language packages needed by your deployment before starting
the server. Translation does not download models at runtime.
