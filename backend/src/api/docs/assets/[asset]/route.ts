import type { MedusaRequest, MedusaResponse } from "@medusajs/framework/http"
import { readFile } from "node:fs/promises"
import { dirname, join } from "node:path"

export async function GET(req: MedusaRequest, res: MedusaResponse) {
  const asset = req.params.asset
  if (asset !== "swagger-ui.css" && asset !== "swagger-ui-bundle.js") {
    return res.status(404).json({ message: "Unknown documentation asset" })
  }
  const root = dirname(require.resolve("swagger-ui-dist/package.json"))
  res.type(asset.endsWith(".css") ? "css" : "js")
  res.setHeader("Cache-Control", "public, max-age=86400")
  res.send(await readFile(join(root, asset)))
}
