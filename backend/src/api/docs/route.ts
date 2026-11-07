import type { MedusaRequest, MedusaResponse } from "@medusajs/framework/http"

export async function GET(_req: MedusaRequest, res: MedusaResponse) {
  res.type("html").send(`<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>MSDSS · Medusa API</title><link rel="stylesheet" href="/docs/assets/swagger-ui.css"></head>
<body style="margin:0"><div id="swagger-ui"></div><script src="/docs/assets/swagger-ui-bundle.js"></script>
<script>SwaggerUIBundle({dom_id:'#swagger-ui',urls:[{name:'Store API · Medusa 2.22.4',url:'/openapi/store'},{name:'Admin API · Medusa 2.22.4',url:'/openapi/admin'}],deepLinking:true,persistAuthorization:false,validatorUrl:null})</script>
</body></html>`)
}
