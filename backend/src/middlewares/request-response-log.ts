import type { MedusaNextFunction, MedusaRequest, MedusaResponse } from "@medusajs/framework/http"
import { appendFile, mkdirSync } from "node:fs"
import { join } from "node:path"
import { randomUUID } from "node:crypto"

const directory = process.env.HTTP_LOG_DIR || "/app/logs"
const limit = 64 * 1024
const sensitive = /password|passwd|secret|token|authorization|cookie|api[-_]?key|credential/i
mkdirSync(directory, { recursive: true, mode: 0o700 })

function redact(value: unknown, depth = 0): unknown {
  if (depth > 10) return "[DEPTH LIMIT]"
  if (typeof value === "string") return value.length > limit ? value.slice(0, limit) + "[TRUNCATED]" : value
  if (Array.isArray(value)) return value.slice(0, 200).map(item => redact(item, depth + 1))
  if (value && typeof value === "object") {
    return Object.fromEntries(Object.entries(value).map(([key, item]) => [
      key, sensitive.test(key) ? "[REDACTED]" : redact(item, depth + 1),
    ]))
  }
  return value ?? null
}

function requestUrl(req: MedusaRequest) {
  const offset = req.originalUrl.indexOf("?")
  if (offset < 0) return req.originalUrl
  const query = new URLSearchParams(req.originalUrl.slice(offset + 1))
  let changed = false
  for (const key of query.keys()) {
    if (sensitive.test(key)) {
      query.set(key, "[REDACTED]")
      changed = true
    }
  }
  return changed ? req.originalUrl.slice(0, offset) + "?" + query : req.originalUrl
}

export function requestResponseLog(req: MedusaRequest, res: MedusaResponse, next: MedusaNextFunction) {
  // Keep API traffic only; omit admin HTML, assets, docs and health checks.
  if (!/^\/(store|admin|auth)(\/|$)/.test(req.originalUrl)) return next()

  const startedAt = new Date()
  const started = performance.now()
  const chunks: Buffer[] = []
  let bytes = 0
  let captured = 0
  let recorded = false

  function capture(chunk: unknown, encoding?: unknown) {
    if (typeof chunk !== "string" && !(chunk instanceof Uint8Array)) return
    const buffer = typeof chunk === "string"
      ? Buffer.from(chunk, typeof encoding === "string" ? encoding as BufferEncoding : "utf8")
      : Buffer.from(chunk)
    bytes += buffer.length
    if (captured < limit) {
      const part = buffer.subarray(0, limit - captured)
      chunks.push(part)
      captured += part.length
    }
  }

  const originalWrite = res.write
  const originalEnd = res.end
  res.write = function (chunk: unknown, ...args: unknown[]) {
    capture(chunk, args[0])
    return Reflect.apply(originalWrite, this, [chunk, ...args])
  } as typeof res.write
  res.end = function (chunk?: unknown, ...args: unknown[]) {
    capture(chunk, args[0])
    return Reflect.apply(originalEnd, this, [chunk, ...args])
  } as typeof res.end

  function record(completed: boolean) {
    if (recorded) return
    recorded = true
    try {
      const contentType = String(res.getHeader("content-type") || "")
      let body: unknown = null
      // Never save raw partial JSON: it may contain unredacted credentials.
      if (bytes > limit) body = { omitted: "Response exceeds 64 KiB" }
      else if (bytes && /json/i.test(contentType)) {
        try { body = redact(JSON.parse(Buffer.concat(chunks).toString("utf8"))) }
        catch { body = { omitted: "Response is not valid JSON" } }
      } else if (bytes) body = { omitted: "Non-JSON response" }

      const entry = {
        id: randomUUID(),
        timestamp: startedAt.toISOString(),
        duration_ms: Math.round((performance.now() - started) * 100) / 100,
        completed,
        request: {
          method: req.method,
          url: requestUrl(req),
          remote_address: req.socket.remoteAddress,
          headers: redact(req.headers),
          body: redact(req.body),
        },
        response: {
          status: res.statusCode,
          headers: redact(res.getHeaders()),
          bytes,
          truncated: bytes > limit,
          body,
        },
      }
      const file = join(directory, `requests-${startedAt.toISOString().slice(0, 10)}.jsonl`)
      appendFile(file, JSON.stringify(entry) + "\n", { mode: 0o600 }, error => {
        if (error) console.error("HTTP log write failed:", error.message)
      })
    } catch (error) {
      console.error("HTTP log record failed:", error instanceof Error ? error.message : "Unknown error")
    }
  }
  res.once("finish", () => record(true))
  res.once("close", () => record(res.writableFinished))
  next()
}
