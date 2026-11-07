# Analysis playbook

Techniques and catalogs for relation-aware auditing. The goal is to know, for each piece of risky code, every way execution and data reach it, and what each path guarantees. Catalogs are starting points: also search for the project's own wrappers around each API, since a wrapper turns every one of its callers into a sink.

## 1. Building the relation graph: finding every caller

Text search finds direct calls. Most missed vulnerabilities hide behind indirect ones. For each symbol under review, work through:

1. **Direct references.** `rg -n -w '<name>'`. Separate the definition, calls, and bare references (a bare reference means the function is passed somewhere, so follow it).
2. **Aliases and re-exports.** `import { a as b }`, `export * from`, barrel/index files, default exports under a different local name, `from m import a as b`, `use x::a as b`, Go package aliases, C# `using` aliases. Search for the new name too.
3. **Methods.** Search `.name(`, `->name(`, `::name(`. When several classes define the same method name, resolve the receiver type. If it cannot be resolved, consider every definition.
4. **Polymorphism.** For an interface, trait, protocol, abstract, or base method, list all implementations and overrides. A call through the interface fans out to all of them, and a call site that reaches one implementation reaches the rest.
5. **Higher-order and stored functions.** Callbacks, handlers in maps and arrays, `bind`/`partial`/closures, promises and futures, goroutines, thread pools, `setTimeout`, `atexit`, finalizers.
6. **Registration and conventions.** Route tables and decorators (`@app.route`, `@GetMapping`, `[HttpPost]`, `router.get`), file-system routing (Next.js `app/` and `pages/`, SvelteKit, Remix, Rails controllers, Django `urls.py`), middleware chains, DI containers and providers, plugin registries, CLI command registries, cron and job schedulers, ORM hooks and model callbacks, serializer hooks, template helpers and filters, framework lifecycle methods.
7. **Events and messages.** `emit('x')`/`on('x')`, signals and receivers, pub/sub topics, queue consumers, webhooks, observers. Search the event, topic, or queue name as a string to link producers to consumers.
8. **Dynamic dispatch.** `getattr`, `send`/`public_send`, `Class.forName`, reflection, `require(variable)`, dynamic `import()`, `call_user_func`, `method_missing`, `__getattr__`, string-keyed handler maps. Find where the string comes from. If an attacker can influence it, that is itself a lead.
9. **Magic and implicit calls.** Constructors and destructors, `__init__`/`__del__`/`__reduce__`/`__eq__`, `toString`/`valueOf`/`toJSON`, getters/setters and property decorators, operator overloads, `Drop`, `Deref`, implicit conversions, static initializers, module top-level code run on import.
10. **Cross-language and cross-process.** SQL views, triggers, and stored procedures; templates referencing server variables; YAML/JSON wiring; generated clients and stubs (map from the spec to the handler); HTTP/IPC calls into the same codebase's services (match the client URL/path to the server route); FFI and native modules; shell scripts invoking project binaries; CI and deploy scripts.
11. **Tests are not callers.** Record them as `tested-by`, not as reachability evidence.

When available, use installed tooling to cross-check: language servers (reference search), `ctags`/`universal-ctags`, `tsc --noEmit`, `pyright`, `go vet`, `gopls references`, `cargo check`, `javap`. Do not install tools.

Record unresolved edges explicitly. "No callers found" is a conclusion that requires all eleven checks. Otherwise write "no static callers; possible dynamic entry via X".

## 2. Contract analysis

For each important symbol, write down its contract and check both sides.

**Preconditions it relies on:** input validated/typed/bounded, caller authenticated and authorized, object ownership or tenant checked, non-null or non-empty, path normalized and inside a root, lock held, transaction open, called once, called after init, trusted origin, correct encoding. For each, find which caller is supposed to guarantee it, then check **every** caller. Missing guarantees on one path are findings, even when other paths are fine.

**Outcomes it produces:** return codes, `null`/`None`/`nil`/`undefined`, empty collections, `Result`/`Option`/`error`, exceptions (declared and undeclared), partial side effects on failure, async rejections. Check every caller for:

- ignored errors (`_ =`, unchecked return, empty `catch`/`except: pass`, `.unwrap()` on untrusted-derived values, `// nolint`);
- a missing `await`, or an unhandled promise or future;
- continuing after a failed authorization or validation call (fail-open);
- misinterpreted sentinels (`-1`, `0`, `""`, `false` versus `null`);
- resource cleanup skipped on the error path.

**Signals of contract drift:** siblings with different guards; documentation or comments claiming checks the body does not do; a safety-sounding name (`sanitize`, `escape`, `isSafe`, `checkPermission`, `validate`) whose implementation misses cases; copies of a function that diverged; a boolean parameter that disables a check, and who passes `true`.

## 3. Sources: where untrusted data enters

- **Network:** URL path params, query strings (including repeated keys that become arrays), headers (`Host`, `X-Forwarded-*`, `Referer`, `Origin`), cookies, request bodies (JSON types can be objects or arrays where strings were expected), multipart field names and filenames, GraphQL arguments and aliases, gRPC and websocket messages, OAuth/OIDC callback params, webhook payloads (is the signature verified before use?).
- **Files:** uploads, archives (entry names), parsed documents (XML, YAML, PDF, images, office files, CSV formulas), user-supplied configuration or plugins.
- **Process:** CLI arguments, environment variables in shared or CI contexts, stdin, IPC, message queues, signals.
- **Stored (second-order):** database rows, caches, object storage, logs, and search indexes originally written from user input; data from other tenants.
- **External:** third-party API responses, DNS results, redirects followed by HTTP clients, package metadata, LLM output.
- **Misplaced trust:** client-side validation, hidden form fields, unverified JWT claims, IDs from the client treated as ownership proof, `X-Forwarded-For` for rate limiting or IP allowlists.

## 4. Sink catalog

Required guard = what must dominate every path to the sink. Patterns are non-exhaustive; also search for project wrappers.

| Class | Required guard | JS/TS | Python | Go | Java/Kotlin | Ruby | PHP | C#/.NET | Rust | C/C++ |
|---|---|---|---|---|---|---|---|---|---|---|
| Command execution | no shell; argv array; allowlisted program; `--` before user args | `child_process.exec`, `execSync`, `spawn` with `shell:true`, `execa` with `shell` | `os.system`, `subprocess.*` with `shell=True`, `os.popen`, `pty.spawn` | `exec.Command("sh","-c",…)` | `Runtime.exec`, `ProcessBuilder` | backticks, `system`, `exec`, `%x`, `Open3`, `open("\|…")` | `exec`, `system`, `shell_exec`, `passthru`, `proc_open`, backticks | `Process.Start` | `Command::new("sh").arg("-c")` | `system`, `popen`, `exec*` |
| SQL / NoSQL | parameter binding; allowlist for identifiers and `ORDER BY` | template-string `query(`, `knex.raw`, `sequelize.query`, `$queryRawUnsafe`, Mongo `$where`, operator injection via object bodies | `cursor.execute(f"…")`, `%`-formatting into SQL, `.raw(`, `.extra(`, `text(` with formatting | `db.Query(fmt.Sprintf…)`, `Exec` with concatenation | `Statement.execute*`, string-built JPQL/HQL, `@Query` with SpEL concat | `find_by_sql`, `where("…#{}")`, `order(params…)`, `pluck` with raw SQL | `mysqli_query`, `PDO::query` with concatenation | `SqlCommand` with concatenation, `FromSqlRaw` | `sqlx::query(&format!…)` | string-built SQL passed to C APIs |
| Code eval / SSTI | never evaluate input; sandboxed templates with no user-controlled template source | `eval`, `new Function`, `vm.run*`, `setTimeout(string)`, template compile from input | `eval`, `exec`, `compile`, `jinja2.Template(input)`, `render_template_string` | `text/template` fed user templates | `ScriptEngine.eval`, SpEL/OGNL/EL evaluation, Velocity/Freemarker from input | `eval`, `instance_eval`, `ERB.new(input)` | `eval`, `assert` (old), `preg_replace /e`, `create_function` | `CSharpScript`, Razor from input | — | — |
| Deserialization | safe formats; type allowlists; no native object deserialization of input | `node-serialize`, `serialize-javascript` eval paths, YAML custom types | `pickle`, `marshal`, `yaml.load` without SafeLoader, `jsonpickle`, `shelve` | `gob` from untrusted input with interface types | `ObjectInputStream.readObject`, XStream, Jackson default typing, SnakeYAML `Yaml()` | `Marshal.load`, `YAML.load` (unsafe), `Oj` object mode | `unserialize`, `phar://` wrappers | `BinaryFormatter`, `TypeNameHandling` not None | `bincode`/`serde` into trait objects rarely — check `typetag` | custom binary parsers |
| Filesystem path | resolve to canonical absolute path, then prefix-check against root with a trailing separator; reject symlinks or use `O_NOFOLLOW`; generate names server-side | `fs.*`, `path.join` with input, `res.sendFile`, `express.static` roots, archive extraction | `open`, `os.path.join` (absolute second argument wins), `send_file`, `shutil`, `tarfile.extractall`, `zipfile` | `os.Open`, `filepath.Join`, `http.ServeFile`, archive extraction | `new File`, `Paths.get`, `ZipEntry.getName` | `File.open`, `send_file`, `Rails.root.join` | `include`/`require` with input, `fopen`, `file_get_contents`, `move_uploaded_file` | `File.*`, `Path.Combine` (absolute second argument wins) | `std::fs::*`, `Path::join` (absolute replaces) | `fopen`, `open`, `realpath` misuse |
| Outbound request (SSRF) | allowlist host/scheme; resolve DNS and check IP ranges after resolution; re-check on redirects; block link-local, metadata, loopback, and private ranges, including IPv6 and encoded forms | `fetch`, `axios`, `got`, `http.request` with a user URL | `requests`, `urllib`, `httpx`, `aiohttp` | `http.Get`, `http.NewRequest` | `URL.openConnection`, `RestTemplate`, `WebClient`, `HttpClient` | `Net::HTTP`, `open-uri` (`open(url)`), `Faraday` | `curl_exec`, `file_get_contents(url)` | `HttpClient`, `WebRequest` | `reqwest`, `ureq`, `hyper` | libcurl |
| HTML / DOM output (XSS) | context-aware auto-escaping; no raw HTML from input; sanitize with an allowlist sanitizer when HTML is required | `innerHTML`, `outerHTML`, `document.write`, `insertAdjacentHTML`, `dangerouslySetInnerHTML`, `v-html`, `[innerHTML]`, `bypassSecurityTrust*`, `href`/`src` with `javascript:` | `Markup(`, `\|safe`, `mark_safe`, `autoescape false` | `template.HTML(`, `text/template` for HTML | JSP `<%= %>`, `th:utext`, unescaped writers | `raw`, `html_safe`, `<%==` | `echo` without `htmlspecialchars` | `Html.Raw`, `MarkupString` | `maud::PreEscaped`, askama `\|safe` | CGI output |
| Redirect | allowlist or relative-path-only; reject `//`, `\\`, schemes | `res.redirect`, `location.href =`, `window.open` | `redirect(`, `HttpResponseRedirect` | `http.Redirect` | `sendRedirect`, `redirect:` | `redirect_to params[…]` | `header("Location: …")` | `Redirect(` | framework redirects | — |
| XML parsing (XXE) | disable DTDs and external entities | `libxmljs` with `noent`, `xml2js` older configurations | `lxml` with `resolve_entities`, `xml.dom.minidom` on untrusted input; prefer `defusedxml` | `encoding/xml` is safe from XXE; check custom entity handling | `DocumentBuilderFactory`, `SAXParserFactory`, `XMLInputFactory` without hardening | `Nokogiri` with `NOENT`/`DTDLOAD` | `simplexml_load_string` with `LIBXML_NOENT` | `XmlDocument` with `XmlResolver` set | `quick-xml` custom entities | libxml2 options |
| Regex (ReDoS) | linear-time engine, or bounded input length, or no nested quantifiers on input | `new RegExp(input)`, nested quantifiers in validators | `re` with nested quantifiers on input | RE2 is linear; check `regexp2` | `Pattern` with nested quantifiers | `Regexp.new(input)` | `preg_*` backtracking | `Regex` without timeout | `fancy-regex` backtracking | PCRE |
| Logging | redact secrets and PII; neutralize newlines for log injection | `console.log(req…)`, logger calls with tokens or passwords | `logging` with `request.*`, `password`, `token` | `log.Printf` with secrets | logger with credentials, Log4Shell-style lookups in old versions | `Rails.logger` with params (check `filter_parameters`) | `error_log` | `ILogger` with secrets | `tracing` with secret fields | `syslog` format strings |
| Crypto and randomness | CSPRNG for tokens; vetted algorithms; unique IV/nonce; constant-time comparison; salted slow password hashing | `Math.random` for tokens, `createCipher` (no IV), `md5`/`sha1` for passwords, `===` on MACs | `random` for tokens, `hashlib.md5` for passwords, `==` on HMACs | `math/rand` for tokens, `==` on MACs | `java.util.Random`, `DES`, `ECB`, `equals` on MACs | `rand`, `Digest::MD5` for passwords | `rand`, `mt_rand`, `md5(password)` | `System.Random`, `MD5`, `==` on tokens | `rand::thread_rng` is fine; check `==` on secrets | `rand()`, `memcmp` on MACs |
| Authentication | verified signatures; algorithm pinned; expiry checked; session rotation on login; lockout/rate limit | `jwt.decode` without verify, `algorithms` not pinned, `none` alg accepted | `jwt.decode(verify=False)`, `options={"verify_signature": False}` | `ParseUnverified` | `parseClaimsJwt` versus `parseClaimsJws` | `JWT.decode(t, nil, false)` | `JWT::decode` without key | `ValidateLifetime=false` | `insecure_disable_signature_validation` | — |
| Headers, cookies, CORS | no CR/LF from input; `Secure`/`HttpOnly`/`SameSite`; CORS origin allowlist without reflection plus credentials | `res.setHeader(input)`, `cors({origin: true, credentials: true})` | `response[header] = input`, `CORS_ALLOW_ALL` | `w.Header().Set` with input | `addHeader` with input | `response.headers[...]` | `header()` with input | `Response.Headers.Add` | framework headers | — |
| Mass assignment | allowlist writable fields | `Object.assign(model, req.body)`, spread into ORM create/update | `Model(**request.json)`, `serializer` with `fields="__all__"` | struct binding of all fields | `@ModelAttribute` binding to entities | `permit!`, `update(params[…])` | `$model->fill($request->all())` | model binding to entities with `[Bind]` missing | `serde` into privileged structs | — |
| Prototype pollution (JS) | reject `__proto__`/`constructor`/`prototype` keys; use null-prototype objects or `Map` | deep merge, `lodash.merge`/`set`/`defaultsDeep` on input, `obj[key1][key2] = value` | — | — | — | — | — | — | — | — |
| Memory safety | bounds and size checks before copy; overflow-checked size arithmetic; lifetimes | native addons | C extensions | `unsafe`, cgo | JNI | C extensions | extensions | `unsafe`, `Marshal` | `unsafe`, `from_raw_parts`, `transmute`, `get_unchecked` | `memcpy`, `strcpy`, `sprintf`, `gets`, `alloca`, index arithmetic, `malloc(n*size)` overflow, use-after-free, double free, format strings |
| Resource exhaustion | limits on body size, upload size, pagination, recursion depth, decompression ratio, and allocation sized by input | `JSON.parse` of unbounded bodies, `bodyParser` without limits | unbounded `read()`, zip bombs | `io.ReadAll` without `LimitReader` | unbounded streams | unbounded reads | `memory_limit` assumptions | unbounded streams | `read_to_end` without cap | unchecked `malloc` |
| Other injection | encode for the target grammar | LDAP, XPath, email headers (`\r\n` in subject/to), CSV formula (`=`, `+`, `-`, `@`), GraphQL string building, log format strings, shell-escaped arguments to `ssh`/`git` (option injection via a leading `-`) |
| LLM / agent tools | treat model output as untrusted; confirm before side effects; scope tool permissions | user or document content in prompts that drive tool calls, shell, SQL, HTTP, or file writes; model output rendered as HTML |

## 5. Guard sufficiency

A guard protects a sink only when all of these hold:

1. **Dominance:** it runs on every path to the sink, including alternate entry points, error and retry paths, background jobs, and admin or debug routes.
2. **Context fit:** it matches the sink's grammar. HTML-body escaping does not protect attributes, URLs, JavaScript, or CSS. SQL value binding does not protect identifiers. Shell quoting depends on the shell.
3. **Order:** it runs after the last decode, normalize, concatenate, or unmarshal step. Validate-then-decode and check-then-join are classic bypasses.
4. **Completeness:** allowlist rather than denylist; handles case, Unicode normalization, alternate encodings (URL, double URL, HTML entities, overlong UTF-8), null bytes, trailing dots and slashes, and both separators on Windows.
5. **Type safety:** input cannot arrive as an array, object, number, or `null` where a string was assumed (`?id[]=`, JSON `{"$ne": null}`).
6. **Atomicity:** no gap between check and use (TOCTOU on files, balances, permissions, or unique names).
7. **Fail-closed:** exceptions, timeouts, or missing configuration deny rather than allow.
8. **Not configurable off in production:** debug flags, environment toggles, and feature flags cannot disable it in production.
9. **Server-side:** client-side checks do not count.

## 6. Authorization, state, and business logic

- **Authorization matrix:** for each entry point, list authentication, role check, object-ownership check, and tenant scoping. Compare sibling handlers (`GET` versus `PATCH` versus `DELETE` on the same resource; v1 versus v2 routes; web versus API versus mobile routes; GraphQL resolvers versus REST). Inconsistency is a strong lead.
- **Object-level (IDOR):** every lookup by an ID the client supplies must be scoped to the owner or tenant in the query itself, not checked afterwards in only some branches.
- **Function-level:** admin and internal routes must be protected at the route, not only hidden in the UI.
- **Multi-tenant isolation:** check queries, caches (keys include the tenant?), file paths, background jobs, search indexes, and exports.
- **State machines:** transitions are validated server-side; terminal states cannot be re-entered; client-supplied state is not trusted.
- **Concurrency:** check-then-act on balances, inventory, coupons, invites, and unique names; missing transactions, locks, or unique constraints; non-idempotent webhook or retry handlers; double submission.
- **Business logic:** negative or zero quantities, integer overflow, rounding and currency, time-zone and expiry boundaries, replayed tokens, discount stacking.

## 7. Non-security defect heuristics

- **Error handling:** swallowed exceptions, errors converted to success, retries without backoff or limit, partial writes without rollback, cleanup skipped on error paths.
- **Resources:** unclosed files, sockets, and DB connections; missing `defer`/`finally`/`using`/`with`; unbounded caches, queues, or goroutines; leaked timers or listeners.
- **Concurrency:** shared mutable state without synchronization, non-atomic read-modify-write, async functions assuming ordering, locks held across awaits or I/O.
- **Boundaries:** off-by-one errors, empty inputs, the first and last page, `0` and `MAX` values, time-zone and DST edges, locale-dependent parsing.
- **Performance:** N+1 queries in loops, unbounded result sets, quadratic algorithms on user-sized input, synchronous I/O on hot paths, missing indexes on filtered columns (check migrations).
- **Duplication and drift:** copies of validation, authorization, or serialization logic that diverged. The weaker copy is often the bug.
- **Dead code:** only after section 1's indirect-caller checks; note feature flags and configuration-driven wiring.
- **Tests:** tests that assert the vulnerable behavior, mocks that hide the real guard, and the absence of tests on the riskiest paths.

## 8. Disproof checklist (before promoting a candidate)

1. **Reachability:** is there a production path from a real entry point? Link it. Test-only, dead, or flag-off code lowers severity or rejects the candidate.
2. **Upstream guards:** middleware, framework validation, schema or type validation, ORM binding, WAF-like filters in code, gateway configuration in the repository. Cite what you checked.
3. **Framework defaults:** auto-escaping, CSRF protection, parameterization, and secure cookies are default in many frameworks. Confirm they are not disabled locally.
4. **Types and constraints:** static types, enums, database constraints, and unique indexes that make the bad state impossible.
5. **Tests:** does a test prove the opposite behavior? Is the test itself correct?
6. **Actor:** is the input controlled only by an already-privileged actor? That lowers severity; record it as a precondition.
7. **Environment:** does deployment configuration in the repository (Docker, infrastructure code, proxy configs) neutralize it?
8. **Strongest counterargument:** write it down and state why it fails. If it does not fail, reject the candidate or lower its confidence.

## 9. Variant analysis

After confirming a finding, generalize it: the same sink with the same missing guard, the same copied idiom, sibling handlers, other implementations of the same interface, and the same helper misused elsewhere. Search the whole scope and list every instance in the finding's Variants field, or state that the search found none. One root cause gets one finding ID; instances with different root causes get their own IDs.

## 10. Independent verification (optional)

For Critical or High findings, when the Agent tool is available, give a fresh subagent only the claim, the linked locations, and the relevant guard hypotheses, and ask it to prove the claim wrong. Do not share your reasoning, to avoid anchoring it. Record whether the refutation succeeded, and adjust the finding if it did.
