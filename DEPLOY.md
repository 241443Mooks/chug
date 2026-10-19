# Deploy the public demo to Cloudflare Pages

This repository has two separate experiences:
- `web/` is the **static, read-only public demo** using precomputed, fictional data. This is what Cloudflare Pages should host.
- `chug/` is the **local Python application**. It must not be deployed as a public unauthenticated service.

## Set up a fresh Git-connected Pages project

1. Open Cloudflare Dashboard > Workers & Pages > Create > Pages > Connect to Git. (Labels may differ by dashboard version.)
2. Select GitHub repository `241443Mooks/chug`. If the repository is not offered, grant it access in the Cloudflare GitHub integration's repository permissions.
3. Configure the project with these settings:

| Field | Value |
| --- | --- |
| Production branch | `main` |
| Framework preset | None |
| Root directory | `web` |
| Build command | Leave blank (no build required) |
| Build output directory | `.` (relative to `web`) |

4. Name the Pages project, for example, `chug-demo`. First deploy to the auto-generated `*.pages.dev` address.
5. **Before changing the custom domain**, check that the new preview works:
   - `/` renders the Home/Queue UI;
   - `/demo-data/queue.json` returns JSON with six items, not HTML;
   - `/demo-data/decision-log.json` has 300 explicitly fictional entries;
   - `/decision-log.html` loads and filters;
   - Falcon Data/T03 and a linked DOCX original open;
   - no decisions/uploads are writable on the public demo.
6. On the new Pages project, open Custom domains and add `chug.smooks.co.uk`. If Cloudflare says this hostname is already assigned to another project, first detach that custom domain from the old Pages project, then attach it to the new one. Do not delete the existing project or modify `smooks.co.uk` itself.
7. Check `https://chug.smooks.co.uk` again and confirm it shows the new deployment. Keep the old project until the new deployment is verified.

## Future updates

A Git-integrated Cloudflare Pages project should build/deploy on pushes to `main`, without manual ZIP uploads or GitHub Actions upload tokens. There are deliberately no Cloudflare deployment workflows or secrets in this repository.

If the account's Pages integration cannot accept a blank command with root `web`, an equivalent fallback is repository root and **build output directory `web`**. Do not combine root `web` with output directory `web` (that incorrectly looks for `web/web`).

## Local application

From the repository root, run:

```sh
python3 -m chug.server --port 8771
```

Visit `http://127.0.0.1:8771`. Only use fictional documents. Do not expose this local server to the public Internet.

## Scope and release check

Deployment is not validation: after GitHub or Cloudflare changes, test the URL and the intended five-minute reviewer experience. Synthetic research specimens and the 300 illustrative decision-log rows are *not* approved legal advice or proven productivity data.
