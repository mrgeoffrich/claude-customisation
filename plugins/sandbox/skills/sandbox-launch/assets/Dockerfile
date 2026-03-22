FROM node:20-bookworm

# Install Claude Code globally
RUN npm install -g @anthropic-ai/claude-code

# Install network/firewall tools and common dev utilities
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       iptables ipset iproute2 dnsutils \
       git curl jq ripgrep sudo \
    && rm -rf /var/lib/apt/lists/*

# Copy firewall init script
COPY init-firewall.py /usr/local/bin/init-firewall.py
RUN chmod +x /usr/local/bin/init-firewall.py

# Allow non-root user to run firewall setup via sudo (and only that)
RUN echo "node ALL=(ALL) NOPASSWD: /usr/bin/python3 /usr/local/bin/init-firewall.py" >> /etc/sudoers.d/node-firewall

# Run as non-root user
USER node
WORKDIR /workspace

ENV NODE_OPTIONS="--max-old-space-size=4096"
