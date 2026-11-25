export const meta = {
  name: 'deep-scan',
  description: 'Bundle-by-bundle deep review of a repo plus re-check of known findings; every finding adversarially verified',
  whenToUse: 'audit-codebase deep scan mode: whole-repo or scoped audit, CodeRabbit / Alibaba open-code-review style',
  phases: [
    { title: 'Recheck', detail: 'fresh skeptics re-test each known finding' },
    { title: 'Review', detail: 'one reviewer per file bundle with a fixed checklist' },
    { title: 'Verify', detail: 'skeptics try to refute each new finding' },
  ],
}

// args: {
//   root: '/abs/repo',
//   bundles: [{ name, paths: [..], focus }],        // ~5-12k lines each; every source file in exactly one bundle
//   known: [{ id, title, file, line, problem, severity, category, fix? }],  // re-checked, and passed to reviewers so they look for NEW issues
//   rules: 'extra read-only/laptop rules for every agent (optional)',
//   load: 'assumed load (optional)',
// }
const A = args || {}
const ROOT = A.root
const BUNDLES = A.bundles || []
const KNOWN = A.known || []
const RULES = `Repo: ${ROOT}. READ-ONLY: change no files, commit nothing, start no servers, run no builds, test suites, typecheck or linters. Skip generated files. ${A.rules || ''}`
const LOAD = A.load || 'state the load you assume from the deploy config and README'

const FINDINGS = {
  type: 'object',
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          title: { type: 'string' },
          file: { type: 'string', description: 'repo-relative path' },
          line: { type: 'string', description: 'line or range' },
          category: { type: 'string', enum: ['bug', 'security', 'data-loss', 'money', 'scale', 'missing-test', 'perf', 'lean'] },
          severity: { type: 'string', enum: ['must', 'should', 'nice'] },
          what: { type: 'string', description: 'what the code does, 1 sentence' },
          problem: { type: 'string', description: 'concrete case: this input/situation leads to this wrong result' },
          fix: { type: 'string', description: 'smallest fix, prefer deleting code' },
          ifSkipped: { type: 'string' },
        },
        required: ['title', 'file', 'line', 'category', 'severity', 'what', 'problem', 'fix', 'ifSkipped'],
      },
    },
    notRead: { type: 'string' },
  },
  required: ['findings', 'notRead'],
}

const VERDICT = {
  type: 'object',
  properties: {
    refuted: { type: 'boolean' },
    reason: { type: 'string', description: 'what you read and why it holds or fails, 1-3 sentences, cite file:line' },
    severity: { type: 'string', enum: ['must', 'should', 'nice'] },
    fix: { type: 'string', description: 'the smallest correct fix as you now see it' },
  },
  required: ['refuted', 'reason', 'severity', 'fix'],
}

const CHECKLIST = `1. Nil/zero/empty: nil deref (incl. nil interfaces), empty slices, zero IDs, last item, off-by-one.
2. Concurrency: check-then-write races, missing locks/FOR UPDATE, shared maps, goroutine/listener leaks, two processes doing the same work.
3. Injection: SQL by concatenation, command/path injection, SSRF, XSS (raw HTML, srcDoc, href from data), header injection.
4. Auth: missing permission/tenant/business scoping (IDOR), CSRF, secrets in code or logs, weak randomness, non-constant-time compares, missing per-target rate limits on guessable codes.
5. Money and side effects: double charge/send/publish on retry, external call inside a DB transaction then rollback, idempotency gaps, cost not recorded.
6. Errors: swallowed errors, errors mapped to success, wrong error class changing retry behaviour, cleanup on an already-cancelled context.
7. Data: writes in wrong order (object deleted before DB commit), missing transaction, soft-deleted rows treated wrongly, time zones, rounding, currency minor units, UTF-8/UTF-16 length, case-folded index used on the original string.
8. Scale: query per item, unbounded memory/lists/maps, missing index on a hot query, O(n^2).
9. Contract: callers that disagree with what a function returns; the same rule implemented differently in two places.
10. Tests: risky logic (money, auth, parsers, data writes) with no test that fails if it breaks.
11. Lean: dead exported code (grep the WHOLE repo incl. tests and apps first), duplicate helpers, pass-through wrappers.`

const knownBlock = KNOWN.length ? `\nAlready reported, do NOT report again (find new ones):\n- ${KNOWN.map((k) => `${k.title} (${k.file}:${k.line})`).join('\n- ')}\n` : ''

const reviewPrompt = (b) => `You are one reviewer in a bundle-by-bundle deep code review (CodeRabbit / Alibaba open-code-review style). Your bundle: ${b.paths.join('; ')}. Focus: ${b.focus || 'general'}.
${RULES}
Assumed load: ${LOAD}.

Read every non-test source file in your bundle fully. Follow calls out of the bundle (callers and callees) to judge a path, but report only issues located in your bundle. Apply this checklist to every file:
${CHECKLIST}
${knownBlock}
Precision over recall: report only issues with a concrete case ("this input leads to this wrong result"). No style, no "consider". A comment starting with "shortcut:" that names its limit is a decision, not a finding. At most 8 findings, most severe first; an empty list is fine. Plain short English.`

const refutePrompt = (f, lens, i) => `You are skeptic #${i + 1} (${lens} lens) checking one code-review finding. REFUTE it if you can. ${RULES}
Finding${f.id ? ' ' + f.id : ''}:
Title: ${f.title}
Where: ${f.file}:${f.line}
${f.what ? 'What the code does: ' + f.what + '\n' : ''}Claimed problem: ${f.problem}
${f.fix ? 'Proposed fix: ' + f.fix + '\n' : ''}
Read the cited code as it is NOW (it may have changed) and everything needed to judge it: callers, callees, middleware, DB constraints/triggers/migrations, tests, docs that record the behaviour as intended. Look for a guard that already prevents the case, the case being impossible, wrong claims about a library or platform, or the code having been fixed. refuted=true if the claim is wrong, already prevented, fixed, or you cannot confirm it from the code. refuted=false only if you traced the path and the wrong result really happens. Give your severity and the smallest correct fix.`

const LENSES = ['correctness', 'does-it-really-happen', 'security-and-money']

const judge = async (f, phase) => {
  const n = f.severity === 'must' ? 2 : 1
  const votes = (await parallel(Array.from({ length: n }, (_, i) => () =>
    agent(refutePrompt(f, LENSES[i % LENSES.length], i), { label: `${phase.toLowerCase()}:${(f.id || f.title).slice(0, 40)}`, phase, schema: VERDICT })))).filter(Boolean)
  const complete = votes.length === n
  const holds = complete && votes.every((v) => !v.refuted)
  const sev = holds ? (votes.some((v) => v.severity === 'must') ? 'must' : votes.some((v) => v.severity === 'should') ? 'should' : 'nice') : f.severity
  return { ...f, holds, incomplete: !complete, severity: sev, fix: holds ? votes[0].fix || f.fix : f.fix, reasons: votes.map((v) => v.reason) }
}

// Known findings are re-checked while the bundles are reviewed; both flows run concurrently (no barrier between them).
const [rechecked, reviewed] = await Promise.all([
  parallel(KNOWN.map((f) => () => judge(f, 'Recheck'))),
  pipeline(
    BUNDLES,
    (b) => agent(reviewPrompt(b), { label: `review:${b.name}`, phase: 'Review', schema: FINDINGS }),
    async (rev, b) => {
      if (!rev) return { bundle: b.name, failed: true, notRead: 'reviewer failed', findings: [] }
      const judged = await parallel(rev.findings.map((f) => () => judge({ ...f, bundle: b.name }, 'Verify')))
      return { bundle: b.name, notRead: rev.notRead, findings: judged.filter(Boolean) }
    },
  ),
])

const re = rechecked.filter(Boolean)
const rev = reviewed.filter(Boolean)
const fresh = rev.flatMap((r) => r.findings)
const failedBundles = BUNDLES.map((b) => b.name).filter((n) => !rev.some((r) => r.bundle === n && !r.failed))
const incomplete = [...re, ...fresh].filter((x) => x.incomplete).map((x) => x.id || x.title)
if (failedBundles.length) log(`bundles with no review: ${failedBundles.join(', ')}`)
if (incomplete.length) log(`${incomplete.length} findings missing a verdict (agent died); rerun with resumeFromRunId`)
log(`recheck: ${re.filter((x) => x.holds).length}/${re.length} hold; new: ${fresh.filter((x) => x.holds).length} hold, ${fresh.filter((x) => !x.holds).length} refuted`)
return {
  recheck: re,
  fresh,
  notRead: rev.map((r) => `${r.bundle}: ${r.notRead}`),
  failedBundles,
  incomplete,
}
