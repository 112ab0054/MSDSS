FROM node:22.22.0-bookworm-slim@sha256:dd9d21971ec4395903fa6143c2b9267d048ae01ca6d3ea96f16cb30df6187d94

ARG AUTH_MFA_ENCRYPTION_KEY
ENV AUTH_MFA_ENCRYPTION_KEY=$AUTH_MFA_ENCRYPTION_KEY

RUN apt-get update && apt-get install -y --no-install-recommends python3 make g++ git ca-certificates \
    && rm -rf /var/lib/apt/lists/* && mkdir /app && chown node:node /app
WORKDIR /app
USER node
ENV NODE_OPTIONS=--max-old-space-size=1536
COPY --chown=node:node package*.json ./
RUN npm ci --legacy-peer-deps --no-audit --no-fund && npm cache clean --force
COPY --chown=node:node . .
# Isolated API fixture only: disable the admin UI in the copied image configuration.
# The source backend/medusa-config.ts and the existing deployment are not modified.
RUN node -e 'const fs=require("fs");const p="medusa-config.ts";const s=fs.readFileSync(p,"utf8");const m="module.exports = defineConfig({";if(!s.includes(m))throw new Error("Unexpected config shape");fs.writeFileSync(p,s.replace(m,m+"\n  admin: { disable: true },"))' \
    && npx medusa build \
    && mkdir -p logs .medusa/server/static/uploads \
    && cp -R static/openapi .medusa/server/static/openapi
ENV NODE_ENV=production NODE_OPTIONS=--max-old-space-size=768
CMD ["sh", "-c", "cd .medusa/server && npm run start"]
