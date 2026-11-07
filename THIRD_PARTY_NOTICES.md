# Third-party source

`backend/src` and `backend/tsconfig.json` originate from the official Medusa starter:
https://github.com/medusajs/medusa-starter-default/tree/9565d9d5487e470137c63824fe58c59a2098bde8

Medusa packages are pinned to 2.22.4. Documentation routes are project additions.

`backend/static/openapi` contains the bundled official Store and Admin specifications
from the Medusa `v2.22.4` tag:
https://github.com/medusajs/medusa/tree/v2.22.4/www/apps/api-reference/specs

The upstream `info.version` value is 2.22.3 even in this tag and is retained.
The `servers` list is changed to the same-origin URL `/` for this deployment.

Medusa is distributed under the MIT license. Swagger UI is distributed under Apache-2.0.
