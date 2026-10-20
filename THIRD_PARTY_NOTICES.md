# Third-Party License Notices

Updated: `2026-10-20`.

## Application License

The project's own application code is licensed under the Apache License,
Version 2.0 (`Apache-2.0`). See [LICENSE](LICENSE). Third-party components retain
their own licenses and notices; the application license does not replace them.

## Valkey Server

The default broker image is `valkey/valkey:8.1.10-alpine`. Its Valkey server
uses BSD-3-Clause. The complete version-specific upstream license and copyright
notices are retained in [LICENSES/Valkey-8.1.10.txt](LICENSES/Valkey-8.1.10.txt).
The file includes the notices for Valkey contributors and Redis Ltd. associated
with inherited code; those notices must be preserved.

Upstream license source:
<https://raw.githubusercontent.com/valkey-io/valkey/8.1.10/COPYING>.

This server license does not describe every package in the Alpine image.
Base-image, native-library, and OS components retain their respective terms.
The former Redis 7 server is not the default broker. Redis-compatible client
libraries, `redis://` URLs, and the legacy Compose hostname `redis` remain in
use; those names do not change the selected server or its license.

## Other Known License References

These references identify known dependency obligations, not a complete SBOM or
a complete set of redistribution materials for every possible installation.

| Component | License reference | Scope |
|---|---|---|
| `psycopg`, `psycopg-binary` | LGPL-3.0-only | Python PostgreSQL/migration dependencies; retain upstream licenses and satisfy applicable redistribution, source-access and replacement obligations. |
| `certifi` | MPL-2.0 | Transitive Python dependency; retain its upstream license and applicable source-access information. |
| `axe-core`, `@axe-core/playwright` | MPL-2.0 | JavaScript development/accessibility-test tooling; not part of the served frontend source. |

Use the license and notice files supplied with the exact installed package
versions. Sources include the [Psycopg license](https://github.com/psycopg/psycopg/blob/master/LICENSE.txt)
and [Mozilla's MPL guidance](https://www.mozilla.org/en-US/MPL/2.0/FAQ/).
Other Python/JavaScript dependencies and external service images also retain
their own terms; they are not relicensed by this notice.

Full release inventories, required source materials, and distribution-specific
obligation verification remain separate from these targeted license references.
