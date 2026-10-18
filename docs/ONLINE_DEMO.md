# Private online demo

This container runs the existing mutual-NDA comparison workflow for synthetic documents. It accepts one DOCX at a time, keeps the original bytes, compares the upload with the selected supported NDA reference, and records reviewer decisions locally. It does not support arbitrary contract families or real/confidential contracts.

## Deployment shape

Build and run the repository's `Dockerfile` on a container host that provides:

- HTTPS at the public URL, with HTTP redirected to HTTPS.
- A private route to the container on its `PORT` (default `8000`). Do not publish the container's port directly around the host's HTTPS/access controls.
- A durable, private, writable volume mounted at `/data`.
- The mounted directory must be writable by the container's UID/GID `10001`; configure the volume ownership or permissions at the host.
- One app instance. The current JSONL ledgers and in-memory review state are a single-process demonstration store; do not scale it horizontally.
- An ingress request-size limit above the app's 2.1 MB multipart ceiling and a modest request rate limit.

Keep the existing read-only website at `chug.smooks.co.uk` unchanged. This interactive backend must run as a separate private container service, because static Pages hosting cannot run the Python upload API. Use a separate private hostname or an equally isolated route.

The container runs as UID/GID `10001`, binds to `0.0.0.0`, and fails at startup unless the private access credentials and exact HTTPS origin are configured. Protect the service with the host's TLS and network controls as well. Keep the platform's access logs free of request bodies and authorization headers.

The Python base image is pinned by digest for repeatable builds. Update that digest deliberately as part of routine base-image security maintenance.

## Required host secrets and settings

Set these in the host's secret/configuration manager. Do not put live values in the repository or build image.

| Setting | Value |
| --- | --- |
| `CHUGCHUG_ONLINE` | `1` |
| `CHUGCHUG_ACCESS_USERNAME` | A dedicated demo username without a colon |
| `CHUGCHUG_ACCESS_PASSWORD` | A unique random password of at least 24 characters |
| `CHUGCHUG_PUBLIC_ORIGIN` | The exact public origin, for example `https://review.example.com` |
| `CHUGCHUG_STATE_DIR` | `/data` |
| `PORT` | The port assigned by the host, or `8000` |

Leave all `CHUGCHUG_AI_*` settings and `OPENAI_API_KEY` unset. The conventional comparison works without sending contract passages to an external provider.

The `CHUGCHUG_PUBLIC_ORIGIN` check rejects browser writes from other origins. The app also requires HTTP Basic authentication on every page and API route; `/healthz` is the only unauthenticated route and returns only `ok` for the host's health probe. Use the exact external HTTPS origin even when TLS terminates at the host's proxy.

The gate is one shared demo credential, not individual accounts or role-based access. Reviewer labels are still entered by the reviewer and are not authenticated identities. Take a private volume snapshot before resetting or replacing a running demo; deleting its volume permanently removes uploaded synthetic files and review history.

## Release procedure

1. Create a private container service from this repository and its `Dockerfile`.
2. Configure the required secrets, HTTPS domain and persistent `/data` volume; set a backup or snapshot policy if the review history needs to survive a host failure.
3. Keep the service to one instance and restrict network access to the HTTPS ingress.
4. Confirm the host reports `/healthz` healthy and redirects public HTTP to HTTPS.
5. Confirm the app asks for credentials, then upload one synthetic DOCX and inspect its source-linked comparison.
6. Restart the service and confirm the upload and review history remain available.
7. Confirm the ingress rejects oversized uploads and applies its request-rate limit.
8. Confirm no real contract, API key or reviewer rationale appears in deployment logs or analytics.

The repository does not identify a hosting account, domain or budget, so this is a portable container configuration and deployment procedure; no hosted URL or live deployment is claimed. Uploads and decision history are stored on `/data`; treat that volume as private even though this demo is limited to synthetic documents.

## Local container smoke run

For a local-only check, build the image and run it with throwaway credentials and a local HTTPS origin value. A reverse proxy is still needed to provide HTTPS before using the online mode in a browser. The normal loopback workflow remains available with `python3 -m chugchug.server --port 8771` and does not require online-mode environment variables.
