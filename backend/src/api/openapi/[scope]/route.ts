import type { MedusaRequest, MedusaResponse } from "@medusajs/framework/http"
import { readFile } from "node:fs/promises"
import { join } from "node:path"

export async function GET(req: MedusaRequest, res: MedusaResponse) {
  const scope = req.params.scope
  if (scope !== "store" && scope !== "admin") {
    return res.status(404).json({ message: "Unknown API specification" })
  }
  const specification = await readFile(join(process.cwd(), "static", "openapi", `${scope}.yaml`))
  res.setHeader("Content-Type", "application/yaml; charset=utf-8")
  res.setHeader("Cache-Control", "public, max-age=3600")
  res.send(specification)
}
