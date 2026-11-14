# Image for `jig ... --sandbox docker`: Claude Code + Node, running as an unprivileged user.
# Build with:  jig sandbox-build
FROM node:22-bookworm-slim

RUN npm install -g @anthropic-ai/claude-code@2.1.325 \
    && npm cache clean --force

USER node
WORKDIR /workspace
ENV HOME=/home/node CI=1
