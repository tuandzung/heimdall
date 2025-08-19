# Heimdall (Python)

FastAPI reimplementation of the original Java [Heimdall](https://github.com/sap1ens/heimdall). Discovers Apache Flink jobs via the Kubernetes Operator CRDs and exposes simple HTTP endpoints.

## Endpoints

- `GET /api/config` — returns selected app configuration
- `GET /api/jobs` — returns list of discovered Flink jobs
- `GET /api/healthz` — health check

### Authentication (optional, Google OAuth)

If enabled, API requests require an authenticated session. The UI exposes a "Login with Google" link.

- `GET /auth/login` — starts Google OAuth flow
- `GET /auth/callback` — OAuth redirect handler
- `GET /auth/me` — returns current session user info
- `POST /auth/logout` — clears the session

## Configuration

Environment variables (pydantic-settings), nested with `__`:

- `HEIMDALL_JOBLOCATOR_K8S_OPERATOR__ENABLED` (default: `true`)
- `HEIMDALL_JOBLOCATOR_K8S_OPERATOR__NAMESPACE_TO_WATCH` (default: `default`)
- `HEIMDALL_JOBLOCATOR_K8S_OPERATOR__LABEL_SELECTOR` (optional label selector used when reading CRs)
- `HEIMDALL_PATTERNS__<KEY>=<VALUE>`
- `HEIMDALL_ENDPOINT_PATH_PATTERNS__<KEY>=<VALUE>`
- `HEIMDALL_APP_VERSION` (optional override)

Authentication (Google OAuth) — disabled by default:

- `HEIMDALL_AUTH__ENABLED` (default: `false`)
- `HEIMDALL_AUTH__GOOGLE_CLIENT_ID`
- `HEIMDALL_AUTH__GOOGLE_CLIENT_SECRET`
- `HEIMDALL_AUTH__REDIRECT_URL` (optional; defaults to detected `/auth/callback` URL)
- `HEIMDALL_AUTH__ALLOWED_EMAILS` (JSON list; optional)
- `HEIMDALL_AUTH__ALLOWED_DOMAINS` (JSON list; optional)
- `HEIMDALL_AUTH__SESSION_SECRET_KEY` (secret used for session cookies)

## Run locally

```bash
uv sync
uv run heimdall
# or run API only
uv run uvicorn heimdall.api:app --reload --port 8080
```

When auth is enabled, ensure the redirect URL configured in Google Cloud Console matches your deployment, e.g.:

```text
http://localhost:8088/auth/callback
```

After logging out from the UI, the page will reload to clear state.

## Notes

- Requires access to a Kubernetes cluster with the Flink Operator CRD installed (`flinkdeployments.flink.apache.org`).
- Uses in-cluster config when running in K8s, else `~/.kube/config`.
