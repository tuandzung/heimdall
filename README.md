# Heimdall (Python)

FastAPI reimplementation of the original Java [Heimdall](https://github.com/sap1ens/heimdall). Discovers Apache Flink jobs via the Kubernetes Operator CRDs and exposes simple HTTP endpoints.

## Endpoints

- `GET /api/config` — returns selected app configuration
- `GET /api/jobs` — returns list of discovered Flink jobs
- `GET /api/healthz` — health check

### Authentication (FastAPI-Users with Google OAuth and JWT)

If enabled, API requests require JWT authentication. The UI supports both Google OAuth and username/password login.

#### OAuth Endpoints (Google)
- `GET /auth/google/authorize` — starts Google OAuth flow
- `GET /auth/google/callback` — OAuth callback and JWT token generation

#### JWT Authentication Endpoints
- `POST /auth/jwt/login` — username/password login (returns JWT token)
- `POST /auth/jwt/logout` — JWT logout
- `POST /auth/register` — user registration

#### User Management Endpoints
- `GET /users/me` — returns current user information
- `PATCH /users/me` — updates current user profile
- `GET /users/{id}` — get user by ID (admin)
- `PATCH /users/{id}` — update user by ID (admin)
- `DELETE /users/{id}` — delete user by ID (admin)

#### Legacy Endpoints (UI compatibility)
- `GET /auth/callback` — legacy UI callback handler

## Configuration

Environment variables (pydantic-settings), nested with `__`:

- `HEIMDALL_JOBLOCATOR_K8S_OPERATOR__ENABLED` (default: `true`)
- `HEIMDALL_JOBLOCATOR_K8S_OPERATOR__NAMESPACE_TO_WATCH` (default: `default`)
- `HEIMDALL_JOBLOCATOR_K8S_OPERATOR__LABEL_SELECTOR` (optional label selector used when reading CRs)
- `HEIMDALL_PATTERNS__<KEY>=<VALUE>`
- `HEIMDALL_ENDPOINT_PATH_PATTERNS__<KEY>=<VALUE>`
- `HEIMDALL_APP_VERSION` (optional override)

Authentication (FastAPI-Users with Google OAuth and JWT) — disabled by default:

- `HEIMDALL_AUTH__ENABLED` (default: `false`)
- `HEIMDALL_AUTH__GOOGLE_CLIENT_ID`
- `HEIMDALL_AUTH__GOOGLE_CLIENT_SECRET`
- `HEIMDALL_AUTH__REDIRECT_URL` (optional; defaults to detected `/auth/google/callback` URL)
- `HEIMDALL_AUTH__ALLOWED_EMAILS` (JSON list; optional)
- `HEIMDALL_AUTH__ALLOWED_DOMAINS` (JSON list; optional)
- `HEIMDALL_AUTH__SESSION_SECRET_KEY` (secret used for JWT tokens)
- `HEIMDALL_AUTH__DATABASE_URL` (default: `sqlite+aiosqlite:///./heimdall.db`)

## Run locally

```bash
uv sync
uv run heimdall
# or run API only
uv run uvicorn heimdall.api:app --reload --port 8080
```

When auth is enabled, ensure the redirect URL configured in Google Cloud Console matches your deployment, e.g.:

```text
http://localhost:8088/auth/google/callback
```

After logging out from the UI, the page will reload to clear state.

## Database

Heimdall uses SQLAlchemy with SQLite by default. The database is automatically created and tables are initialized on first run. To use a different database, set the `HEIMDALL_AUTH__DATABASE_URL` environment variable to a supported SQLAlchemy connection string.

Supported databases:
- SQLite (default): `sqlite+aiosqlite:///./heimdall.db`
- PostgreSQL: `postgresql+asyncpg://user:password@localhost/heimdall`
- MySQL: `mysql+aiomysql://user:password@localhost/heimdall`

## Notes

- Requires access to a Kubernetes cluster with the Flink Operator CRD installed (`flinkdeployments.flink.apache.org`).
- Uses in-cluster config when running in K8s, else `~/.kube/config`.
