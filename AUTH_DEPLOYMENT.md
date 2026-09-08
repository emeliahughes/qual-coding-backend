# Private deployment setup

The application now denies anonymous access to every project and coding route. Before restarting production, create the authentication tables and the first administrator.

## Required production configuration

Set these environment variables for the WSGI service:

- `SECRET_KEY`: a persistent random value of at least 32 bytes;
- `APP_ORIGINS=https://qual-coder.com`;
- `SESSION_COOKIE_SECURE=true`; and
- `SESSION_HOURS=12` or the desired session lifetime.

If `SECRET_KEY` is omitted, the application creates `data/.session_secret` with owner-only permissions. An explicit service-managed secret is preferred for production backups and multi-process deployments.

## Database migration and first administrator

Back up `data/database.db`, then run:

```sh
venv/bin/python migrate_auth.py --username YOUR_USERNAME --display-name "YOUR NAME"
```

The command creates only missing tables and prompts for a password without echoing it. It does not modify existing projects, coders, or results.

Restart the backend after migration, deploy the rebuilt frontend, and sign in as the administrator. Use **Manage researchers** to create named accounts and assign each researcher to a project and coder identity.

## Deployment verification

Before considering the site private, verify all of the following in a signed-out browser:

1. `/api/projects` returns HTTP 401.
2. `/api/project-info?project=KNOWN_SLUG` returns HTTP 401.
3. `/api/download-results?project=KNOWN_SLUG` returns HTTP 401.
4. The application shows only the sign-in page.
5. A researcher sees only assigned projects and cannot code under another coder's identity.

The Git repositories do not contain the production service or web-server configuration, so deployment and service restart must be performed on the host separately.
