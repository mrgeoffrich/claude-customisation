FROM docker/sandbox-templates:claude-code

# Label with base image for staleness detection.
# build-template.py compares this against the current base digest.
ARG BASE_DIGEST=unknown
LABEL cc-sandbox.base-digest="${BASE_DIGEST}"

USER root

# Install Starship prompt to /usr/local/bin (available to all users)
RUN curl -sS https://starship.rs/install.sh | sh -s -- --yes --bin-dir /usr/local/bin

USER agent

# Bake static shell config into .bashrc
RUN printf '\n# cc-sandbox: static config\nalias yolo='"'"'claude --dangerously-skip-permissions'"'"'\nalias ls='"'"'ls --color=auto'"'"'\neval "$(starship init bash)"\n' >> ~/.bashrc

# Bake Claude Code permissions (bypassPermissions + skip dangerous prompt)
RUN mkdir -p ~/.claude && \
    printf '{\n  "permissions": {\n    "defaultMode": "bypassPermissions"\n  },\n  "skipDangerousModePermissionPrompt": true\n}\n' > ~/.claude/settings.json
