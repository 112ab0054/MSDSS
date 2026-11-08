import { defineConfig, loadEnv, Modules } from "@medusajs/framework/utils"

loadEnv(process.env.NODE_ENV || "development", process.cwd())

module.exports = defineConfig({
  featureFlags: {
    translation: true,
  },
  projectConfig: {
    databaseUrl: process.env.DATABASE_URL,
    redisUrl: process.env.REDIS_URL,
    workerMode: "shared",
    cookieOptions: {
      secure: process.env.COOKIE_SECURE !== "false",
      sameSite: "lax",
    },
    http: {
      storeCors: process.env.STORE_CORS!,
      adminCors: process.env.ADMIN_CORS!,
      authCors: process.env.AUTH_CORS!,
      jwtSecret: process.env.JWT_SECRET!,
      cookieSecret: process.env.COOKIE_SECRET!,
    },
  },
  modules: [
    {
      resolve: "@medusajs/medusa/auth",
      dependencies: [Modules.CACHE],
      options: {
        mfa: { encryption_key: process.env.AUTH_MFA_ENCRYPTION_KEY },
        providers: [{
          resolve: "@medusajs/medusa/auth-emailpass",
          id: "emailpass",
        }],
      },
    },
    { resolve: "@medusajs/medusa/translation" },
    {
      resolve: "@medusajs/medusa/file",
      options: {
        providers: [{
          resolve: "@medusajs/medusa/file-local",
          id: "local",
          options: {
            upload_dir: "static/uploads",
            backend_url: `${process.env.PUBLIC_URL}/static/uploads`,
          },
        }],
      },
    },
    {
      resolve: "@medusajs/medusa/caching",
      options: {
        providers: [{
          resolve: "@medusajs/caching-redis",
          id: "caching-redis",
          is_default: true,
          options: { redisUrl: process.env.REDIS_URL },
        }],
      },
    },
    {
      resolve: "@medusajs/medusa/event-bus-redis",
      options: { redisUrl: process.env.REDIS_URL },
    },
    {
      resolve: "@medusajs/medusa/workflow-engine-redis",
      options: { redis: { redisUrl: process.env.REDIS_URL } },
    },
    {
      resolve: "@medusajs/medusa/locking",
      options: {
        providers: [{
          resolve: "@medusajs/medusa/locking-redis",
          id: "locking-redis",
          is_default: true,
          options: { redisUrl: process.env.REDIS_URL },
        }],
      },
    },
  ],
})
