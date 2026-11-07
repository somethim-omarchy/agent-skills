# Fix playbook

For each defect class: where the fix belongs, what a correct fix looks like, and which negative tests must pass before the finding counts as resolved. Pick the classes that apply. A fix that passes the regression test but fails a relevant bypass test is not done.

## General rules

- Fix at the owner of the invariant, at the choke point every path shares.
- Prefer making the unsafe thing impossible over detecting it: typed or structured APIs, allowlists, and canonicalization before checks.
- Fail closed. Missing configuration, parse errors, and timeouts must deny.
- One behavior change per finding. Keep refactors out unless they are the fix.
- Every new rejection path needs a test that proves legitimate input still works.

## Injection family

**SQL / NoSQL**
- Fix: bind every value as a parameter. For identifiers (`ORDER BY`, column or table names), map user choices through an allowlist to constants. For NoSQL, coerce input to the expected scalar type and reject objects where scalars are expected.
- Negative tests: quote and comment characters in values; `ORDER BY` injection (`name; DROP`, `(CASE …)`); operator objects (`{"$ne": null}`, `{"$gt": ""}`); arrays where a scalar was expected; numeric strings; very long input.

**Command execution**
- Fix: call the program directly with an argv array and no shell. Allowlist the program and its subcommands. Put `--` before user-supplied positional arguments. Validate that arguments cannot start with `-`.
- Negative tests: `;`, `&&`, `|`, backticks, `$()`, newlines; leading `-`/`--` option injection (`--upload-pack=`, `-oProxyCommand=`); spaces and quotes; very long input.

**Template / code evaluation**
- Fix: remove evaluation of user input. Pass user data as template variables, never as template source. Use sandboxed engines only when user templates are a product requirement.
- Negative tests: `{{7*7}}`, `${7*7}`, `<%= 7*7 %>`, `#{7*7}`; object-graph traversal payloads for the specific engine.

**XSS**
- Fix: rely on context-aware auto-escaping. Remove raw-HTML sinks. When HTML is required, sanitize with an allowlist sanitizer on output. Validate URL schemes (`http`, `https`, `mailto`) for `href`/`src`. Set a CSP as defense in depth, not as the fix.
- Negative tests: `<script>`, `<img onerror>`, `<svg onload>`; attribute breakouts (`" onmouseover=`); `javascript:` and `data:` URLs with mixed case, whitespace, and entities; payloads inside JSON embedded in HTML; stored (second-order) payloads rendered in admin views.

**Header, log, email, CSV, and LDAP injection**
- Fix: reject or strip CR/LF for headers and log lines; encode for the target grammar; prefix CSV cells starting with `=`, `+`, `-`, `@`, tab, or CR; use library escaping for LDAP and XPath.
- Negative tests: `\r\n`, `%0d%0a`, Unicode line separators; formula prefixes; LDAP metacharacters `*()\`.

## Filesystem and network

**Path traversal / arbitrary file access**
- Fix: generate server-side names when possible. Otherwise resolve to a canonical absolute path (after decoding), then check that it starts with the root plus a separator. Reject symlinks, or open with no-follow semantics. Validate archive entry names the same way before extraction.
- Negative tests: `../`, `..\`, URL-encoded and double-encoded variants (`%2e%2e%2f`, `%252e`), absolute paths (`/etc/passwd`, `C:\`), a sibling-prefix bypass (`/data-evil` versus `/data`), null bytes, trailing dots and spaces (Windows), symlink inside the root pointing outside, zip-slip entries, Unicode normalization variants.

**SSRF**
- Fix: allowlist schemes and hosts. Resolve DNS, check every resolved IP against the deny ranges, and connect to the checked IP (to prevent DNS rebinding). Disable redirects or re-validate each hop. Reject credentials in URLs.
- Negative tests: `127.0.0.1`, `localhost`, `0.0.0.0`, `[::1]`, `[::ffff:127.0.0.1]`, decimal/octal/hex IPs (`2130706433`, `0177.0.0.1`), `169.254.169.254` and metadata hostnames, private ranges, a redirect from an allowed host to a denied one, `user@host` confusion, alternate schemes (`file:`, `gopher:`, `dict:`).

**Open redirect**
- Fix: allow only relative paths, or map to an allowlist of destinations.
- Negative tests: `//evil.com`, `/\evil.com`, `\\evil.com`, `https:evil.com`, `%2f%2fevil.com`, `javascript:`, whitespace and control-character prefixes.

**XXE**
- Fix: disable DTDs and external entities in the parser factory used everywhere; centralize parser construction.
- Negative tests: an external entity pointing at a local file; a billion-laughs expansion; a parameter entity.

## Deserialization

- Fix: switch to data-only formats (JSON with schema validation). Where native deserialization must remain, use strict type allowlists and signed payloads verified before parsing.
- Negative tests: unexpected types in the payload; a tampered signature; oversized or deeply nested input.

## Authentication, authorization, and sessions

**Missing or inconsistent authorization / IDOR**
- Fix: enforce in one policy layer, and scope data access by owner or tenant inside the query (`WHERE id = ? AND tenant_id = ?`), not with a check after fetching. Apply the policy to every sibling route and every twin interface (REST, GraphQL, RPC, admin, export, background job).
- Negative tests: another user's ID; another tenant's ID; an unauthenticated request; a lower-role user; each sibling verb and route; bulk and list endpoints (filtering); IDs in body versus path versus query; exports and downloads.

**Token / JWT / session**
- Fix: verify signatures with a pinned algorithm and key; check `exp`, `nbf`, `aud`, and `iss`; rotate the session on login and privilege change; invalidate on logout and password change.
- Negative tests: `alg: none`; an HS/RS confusion token; an expired token; a wrong audience; a tampered payload; a replayed token after logout.

**CSRF**
- Fix: framework CSRF protection on all state-changing routes, `SameSite` cookies, and no state changes on `GET`.
- Negative tests: a cross-origin form post without a token; a `GET` that tries to change state.

**Password and secret handling**
- Fix: a slow salted hash (argon2, bcrypt, scrypt); constant-time comparison for tokens and MACs; a CSPRNG for tokens; secrets from the environment or a secret store, never from source; redaction at the logger.
- Negative tests: timing-safe comparison used (assert the API call); tokens have the expected entropy and length; secret values absent from logs and error responses.

## State and concurrency

- Fix: make check-then-act atomic with a transaction at the right isolation level, a conditional update (`UPDATE … WHERE balance >= ?`), a unique constraint, or a lock with an owner and timeout. Make webhook and retry handlers idempotent with idempotency keys.
- Negative tests: concurrent execution of the same operation (spawn N parallel calls and assert the invariant holds); retry after partial failure; duplicate delivery of the same event.

## Resource exhaustion

- Fix: limits at the boundary (body size, upload size, page size, recursion depth, decompression ratio, regex input length), and timeouts on outbound calls.
- Negative tests: input just over each limit is rejected cleanly, input at the limit is accepted, a pathological regex input completes within a time bound, and a zip bomb is rejected.

## Mass assignment and prototype pollution

- Fix: explicit allowlists of writable fields per role. For prototype pollution, reject `__proto__`, `constructor`, and `prototype` keys in merges and path setters, or use `Map` and null-prototype objects.
- Negative tests: posting `role`, `isAdmin`, `ownerId`, or `tenantId`; nested `__proto__` and `constructor.prototype` payloads, then asserting `({}).polluted === undefined`.

## Memory safety (C/C++/unsafe Rust)

- Fix: bounds checks before copying, overflow-checked size arithmetic, length-carrying safe APIs, and clear ownership. In Rust, shrink `unsafe` blocks and document their invariants.
- Negative tests: zero-length, maximum-length, and one-over-maximum inputs; size arithmetic near integer limits; run under sanitizers (ASan, UBSan) or Miri when already configured.

## Correctness and error handling

- Fix: handle or propagate every error at the layer that can act on it; restore invariants on failure (rollback, cleanup in `finally`/`defer`/RAII); make boundary conditions explicit.
- Negative tests: the failure of each dependency call in the path (inject errors via existing test seams); empty, first, last, and maximum inputs; time-zone and DST edges when time is involved.

## Performance

- Fix: batch or join N+1 queries, bound result sets, add indexes via migrations when authorized, move blocking I/O off hot paths.
- Tests: a query-count assertion or a bounded-time test on a representative dataset where the repository has such tooling. Otherwise, a documented trace of the before/after query plan or call count.

## Duplication and drift

- Fix: consolidate onto the correct (strictest) implementation, and route every copy through it. Check that the weaker copies' callers still work.
- Tests: the same behavioral test applied to every former copy's entry point.
