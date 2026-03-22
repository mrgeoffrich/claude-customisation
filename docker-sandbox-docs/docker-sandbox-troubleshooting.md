# Docker Sandbox Troubleshooting

> Source: https://docs.docker.com/ai/sandboxes/troubleshooting/

## Common issues

### 'sandbox' is not a docker command

Check that the CLI plugin exists and is executable:

```bash
ls -la ~/.docker/cli-plugins/docker-sandbox
```

Restart Docker Desktop if the plugin file exists but the command isn't recognized.

### Experimental Features locked

An administrator must set `allowBetaFeatures` in the Docker Desktop Settings Management
JSON to enable sandbox features.

### Authentication failure

Invalid or expired API key. Verify `ANTHROPIC_API_KEY` is set correctly in your shell
profile and Docker Desktop was restarted after the change.

### Workspace contains API key config

If `.claude.json` in your workspace has a `primaryApiKey` field, Docker warns about it.
Remove the field or proceed — sandbox credentials take precedence.

### Permission denied on workspace files

Check Docker Desktop's File Sharing settings. Add missing directories and verify `chmod`
permissions allow Docker to read/write.

### Windows crashes with multiple sandboxes

Kill `docker.openvmm.exe` processes in Task Manager, then launch sandboxes sequentially
instead of in parallel.

### Sandbox won't start or behaves unexpectedly

Nuclear option — reset all sandbox state:

```bash
docker sandbox reset
```

This stops all VMs, removes state from `~/.docker/sandboxes/vm/`, clears the image cache,
and purges internal registries.

## Key file paths

| Path | Purpose |
|------|---------|
| `~/.docker/cli-plugins/docker-sandbox` | CLI plugin binary |
| `~/.docker/sandboxes/vm/` | Sandbox VM state |
| `~/.docker/sandboxes/image-cache/` | Image cache |
| `~/.docker/sandboxes/vm/[name]/proxy-config.json` | Per-sandbox network config |
| `~/.sandboxd/proxy-config.json` | Default network config |

## GitHub token not working inside sandbox

The token must be exported in your shell profile (`~/.zshrc` or `~/.bashrc`), not just the
current session. Docker Desktop's daemon reads env vars at startup.

After adding the token:
1. Source the profile file
2. **Restart Docker Desktop** (quit fully and relaunch)
3. If a sandbox already existed, **remove and recreate** it — the credential proxy only
   picks up tokens at sandbox creation time
