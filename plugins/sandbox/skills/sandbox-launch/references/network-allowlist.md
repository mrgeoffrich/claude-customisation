# Network Allowlist Reference

## Package manager to domain mapping

Use this table to determine which domains to allow based on the project's package managers.

| Detected file(s) | Package manager | Domains to allow |
|-------------------|----------------|-----------------|
| `package.json`, `package-lock.json` | npm | `registry.npmjs.org`, `*.npmjs.org` |
| `yarn.lock` | Yarn | `registry.yarnpkg.com`, `*.npmjs.org` |
| `pnpm-lock.yaml` | pnpm | `registry.npmjs.org` |
| `requirements.txt`, `pyproject.toml`, `Pipfile` | pip | `pypi.org`, `files.pythonhosted.org` |
| `Gemfile`, `Gemfile.lock` | Bundler | `rubygems.org`, `index.rubygems.org` |
| `go.mod` | Go modules | `proxy.golang.org`, `sum.golang.org`, `storage.googleapis.com` |
| `Cargo.toml`, `Cargo.lock` | Cargo | `crates.io`, `static.crates.io`, `index.crates.io` |
| `.github/` directory | GitHub Actions | `github.com`, `*.github.com`, `*.githubusercontent.com` |

Always include these Claude Code infrastructure domains regardless of project type:
- `api.anthropic.com`
- `statsig.anthropic.com`
- `statsig.com`
- `sentry.io`

## Network configuration

### Deny-by-default with specific allowlist

```bash
docker sandbox network proxy <sandbox-name> \
  --policy deny \
  --allow-host "api.anthropic.com" \
  --allow-host "statsig.anthropic.com" \
  --allow-host "sentry.io" \
  --allow-host "registry.npmjs.org" \
  --allow-host "*.npmjs.org"
```

### Domain matching rules

- `example.com` — matches the root domain only (does NOT match `api.example.com`)
- `*.example.com` — matches all subdomains (does NOT match `example.com` itself)
- `example.com:443` — matches a specific port
- You typically need **both** `example.com` and `*.example.com` for full access to a service

### Bypass MITM for cert-pinned services

Some services use certificate pinning and will reject the proxy's TLS certificate. Use `--bypass-host` to create a direct TCP tunnel (no credential injection is possible for bypassed hosts):

```bash
docker sandbox network proxy <sandbox-name> \
  --bypass-host api.cert-pinned-service.com
```

### Monitor network activity

```bash
docker sandbox network log
```

### Configuration persistence

- Per-sandbox: `~/.docker/sandboxes/vm/<sandbox-name>/proxy-config.json`
- Defaults for new sandboxes: `~/.sandboxd/proxy-config.json`

### Custom API domains

If the project calls external APIs, add their domains with `--allow-host`. Check `.env`, `.env.example`, or config files for API base URLs.
