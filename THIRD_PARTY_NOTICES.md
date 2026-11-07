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

`storefront/` originates from the maintained official DTC starter at:
https://github.com/medusajs/dtc-starter/tree/4a1d53dc434ed124a78c4e2c9f312e1f47d4e9eb/apps/storefront

Deployment changes add a standalone Docker build, internal backend routing, and a
configurable cookie Secure flag for the current HTTP-only lab. Upstream design and
commerce flows are retained. Next.js and its ESLint configuration are updated to
16.4.5 to address the advisories reported for the upstream 16.3.8 dependency.

`backend/src/search/` and `backend/src/api/middlewares.ts` are copied from the
same official DTC starter commit. They supply the product index and Store Search
access configuration required by its storefront listing, filters, and sorting.
