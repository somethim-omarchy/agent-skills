#!/usr/bin/env python3
"""Rebuild and check the audit/ issue index.

Usage:
  audit_index.py [--repo PATH] check
  audit_index.py [--repo PATH] rebuild [--dry-run]

check    Validate issue headers and statuses, index <-> file agreement, the
         counts line, and that every Markdown link and #L line anchor in
         audit/ resolves. Exit 1 on errors; warnings do not fail.
rebuild  Regenerate the "## Issues" section of audit/REPORT.md (counts line
         and table) from the issue files' headers. Other lines in the section
         are kept after the table. --dry-run prints the section instead of
         writing it.

Standard library only. Links use repository-root form (/path#L42); relative
links are resolved from the linking file's directory.
"""

import argparse
import os
import re
import subprocess
import sys

STATUS_BASES = ["Candidate", "Open", "In progress", "Blocked", "Resolved", "Rejected", "Superseded"]
GROUP_ORDER = {"Open": 0, "In progress": 0, "Blocked": 1, "Candidate": 2,
               "Resolved": 3, "Superseded": 4, "Rejected": 5}
SEVERITY_RANK = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
CONFIDENCE_OK = {"Confirmed", "High", "Moderate", "Suspected", "", "—", "-"}
CONFIDENCE_LEGACY = {"Likely": "High"}
REQUIRED_FIELDS = ["Status", "Severity", "Confidence", "Category", "Updated"]

H1_RE = re.compile(r"^#\s+(F-\d{3,})\s+[—–-]\s+(.+?)\s*$")
FIELD_RE = re.compile(r"^-\s+([A-Za-z][A-Za-z ]*?):\s*(.*)$")
LINK_RE = re.compile(r"\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
ANCHOR_RE = re.compile(r"^L(\d+)(?:-L?(\d+))?$")
ROW_ID_RE = re.compile(r"^\|\s*\[(F-\d{3,})\]\(([^)]+)\)\s*\|")


def repo_root(arg):
    if arg:
        return os.path.abspath(arg)
    try:
        out = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True)
        return out.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return os.getcwd()


def status_base(status):
    s = status.strip()
    for base in STATUS_BASES:
        if s == base or s.startswith(base + " ") or s.startswith(base + "("):
            return base
    return None


def status_display(status):
    base = status_base(status)
    if base == "Superseded":
        m = re.match(r"Superseded by (F-\d{3,})", status.strip())
        return "Superseded by " + m.group(1) if m else "Superseded"
    return base or status.strip()


def severity_key(sev):
    s = sev.strip()
    if s in SEVERITY_RANK:
        return SEVERITY_RANK[s]
    m = re.match(r"likely\s+(\w+)", s, re.I)
    if m and m.group(1).capitalize() in SEVERITY_RANK:
        return SEVERITY_RANK[m.group(1).capitalize()] + 0.5
    return 9


def id_num(issue_id):
    return int(issue_id.split("-")[1])


def parse_issue(path):
    with open(path, encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    issue = {"path": path, "file": os.path.basename(path), "fields": {}, "sections": {}, "errors": []}
    h1 = next((l for l in lines if l.startswith("# ")), None)
    m = H1_RE.match(h1 or "")
    if not m:
        issue["errors"].append("missing or malformed H1 '# F-NNN — Title'")
        issue["id"], issue["title"] = None, ""
    else:
        issue["id"], issue["title"] = m.group(1), m.group(2)
    in_header = True
    current = None
    for line in lines:
        if line.startswith("## "):
            in_header = False
            current = line[3:].strip()
            issue["sections"][current] = []
            continue
        if in_header:
            fm = FIELD_RE.match(line)
            if fm:
                issue["fields"].setdefault(fm.group(1).strip(), fm.group(2).strip())
        elif current is not None:
            issue["sections"][current].append(line)
    return issue


def load_issues(audit_dir):
    issues_dir = os.path.join(audit_dir, "issues")
    if not os.path.isdir(issues_dir):
        return []
    return [parse_issue(os.path.join(issues_dir, f))
            for f in sorted(os.listdir(issues_dir)) if re.match(r"F-\d{3,}.*\.md$", f)]


def counts(issues):
    c = {b: 0 for b in STATUS_BASES}
    sev = {k: 0 for k in SEVERITY_RANK}
    for i in issues:
        base = status_base(i["fields"].get("Status", ""))
        if base:
            c[base] += 1
        if base == "Open" and i["fields"].get("Severity", "").strip() in sev:
            sev[i["fields"]["Severity"].strip()] += 1
    line = ("Counts: open {o} (Critical {cr}, High {h}, Medium {m}, Low {l}) · candidates {ca} · "
            "in progress {ip} · blocked {b} · resolved {r} · rejected {rj}").format(
        o=c["Open"], cr=sev["Critical"], h=sev["High"], m=sev["Medium"], l=sev["Low"],
        ca=c["Candidate"], ip=c["In progress"], b=c["Blocked"], r=c["Resolved"], rj=c["Rejected"])
    if c["Superseded"]:
        line += " · superseded {}".format(c["Superseded"])
    return line


def table(issues):
    def key(i):
        base = status_base(i["fields"].get("Status", "")) or "Candidate"
        return (GROUP_ORDER.get(base, 9), severity_key(i["fields"].get("Severity", "")), id_num(i["id"]))
    rows = ["| ID | Title | Status | Severity | Confidence | Category | Updated |",
            "|---|---|---|---|---|---|---|"]
    for i in sorted((i for i in issues if i["id"]), key=key):
        f = i["fields"]
        updated = (re.match(r"\d{4}-\d{2}-\d{2}", f.get("Updated", "")) or [""])[0]
        cells = ["[{}](/audit/issues/{})".format(i["id"], i["file"]),
                 i["title"].replace("|", "\\|"),
                 status_display(f.get("Status", "")),
                 f.get("Severity", "").split(" (")[0],
                 f.get("Confidence", "").split(" (")[0],
                 f.get("Category", ""),
                 updated]
        rows.append("| " + " | ".join(cells) + " |")
    return rows


def split_sections(text):
    lines = text.splitlines()
    start = next((n for n, l in enumerate(lines) if l.strip() == "## Issues"), None)
    if start is None:
        return lines, None, None
    end = next((n for n in range(start + 1, len(lines)) if lines[n].startswith("## ")), len(lines))
    return lines, start, end


def rebuild(root, dry_run):
    audit_dir = os.path.join(root, "audit")
    report = os.path.join(audit_dir, "REPORT.md")
    issues = load_issues(audit_dir)
    with open(report, encoding="utf-8") as fh:
        text = fh.read()
    lines, start, end = split_sections(text)
    kept = []
    if start is not None:
        for l in lines[start + 1:end]:
            if l.startswith("|") or l.startswith("Counts:"):
                continue
            kept.append(l)
    while kept and not kept[0].strip():
        kept.pop(0)
    while kept and not kept[-1].strip():
        kept.pop()
    section = ["## Issues", "", counts(issues), ""] + table(issues)
    if kept:
        section += [""] + kept
    section.append("")
    if dry_run:
        print("\n".join(section))
        return 0
    if start is None:
        new = lines + [""] + section
    else:
        new = lines[:start] + section + lines[end:]
    with open(report, "w", encoding="utf-8") as fh:
        fh.write("\n".join(new).rstrip("\n") + "\n")
    print("rebuilt {} ({} issues)".format(os.path.relpath(report, root), len(issues)))
    return 0


def link_targets(line):
    """Yield Markdown link destinations, allowing balanced parentheses
    inside them (e.g. Next.js route groups like app/(app)/page.tsx)."""
    pos = 0
    while True:
        start = line.find("](", pos)
        if start < 0:
            return
        i = start + 2
        depth = 0
        while i < len(line):
            ch = line[i]
            if ch == "(":
                depth += 1
            elif ch == ")":
                if depth == 0:
                    break
                depth -= 1
            elif ch.isspace():
                break
            i += 1
        target = line[start + 2:i]
        if target:
            yield target
        pos = i


def md_links(path):
    with open(path, encoding="utf-8") as fh:
        in_fence = False
        for n, line in enumerate(fh, 1):
            if line.lstrip().startswith(("```", "~~~")):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            for target in link_targets(line):
                yield n, target


def check(root):
    audit_dir = os.path.join(root, "audit")
    errors, warnings = [], []
    if not os.path.isdir(audit_dir):
        print("error: no audit/ directory under " + root)
        return 1
    issues = load_issues(audit_dir)
    seen = {}
    for i in issues:
        rel = os.path.relpath(i["path"], root)
        for e in i["errors"]:
            errors.append("{}: {}".format(rel, e))
        if i["id"]:
            if not i["file"].startswith(i["id"] + "-"):
                errors.append("{}: H1 id {} does not match filename".format(rel, i["id"]))
            if i["id"] in seen:
                errors.append("{}: duplicate id {} (also {})".format(rel, i["id"], seen[i["id"]]))
            seen[i["id"]] = rel
        f = i["fields"]
        for field in REQUIRED_FIELDS:
            if field not in f:
                errors.append("{}: missing header field '{}'".format(rel, field))
        base = status_base(f.get("Status", ""))
        if "Status" in f and not base:
            errors.append("{}: unknown status '{}'".format(rel, f["Status"]))
        conf = f.get("Confidence", "").split(" (")[0].strip()
        if conf in CONFIDENCE_LEGACY:
            warnings.append("{}: confidence '{}' is legacy; contract term is '{}'".format(rel, conf, CONFIDENCE_LEGACY[conf]))
        elif "Confidence" in f and conf not in CONFIDENCE_OK:
            warnings.append("{}: non-standard confidence '{}'".format(rel, conf))
        if base in ("Open", "In progress"):
            fix = [l for l in i["sections"].get("Proposed fix", []) if l.strip()]
            if not fix:
                errors.append("{}: {} issue has no Proposed fix".format(rel, base))
            sev = f.get("Severity", "").strip()
            if sev not in SEVERITY_RANK:
                errors.append("{}: {} issue needs a calibrated severity, found '{}'".format(rel, base, sev))

    report = os.path.join(audit_dir, "REPORT.md")
    if os.path.isfile(report):
        with open(report, encoding="utf-8") as fh:
            text = fh.read()
        lines, start, end = split_sections(text)
        if start is None:
            errors.append("audit/REPORT.md: no '## Issues' section")
        else:
            rows = {}
            counts_line = None
            for l in lines[start + 1:end]:
                m = ROW_ID_RE.match(l)
                if m:
                    cells = [c.strip() for c in l.strip().strip("|").split("|")]
                    rows[m.group(1)] = cells
                elif l.startswith("Counts:"):
                    counts_line = l.strip()
            by_id = {i["id"]: i for i in issues if i["id"]}
            for missing in sorted(set(by_id) - set(rows), key=id_num):
                errors.append("audit/REPORT.md: index lacks {}".format(missing))
            for extra in sorted(set(rows) - set(by_id), key=id_num):
                errors.append("audit/REPORT.md: index lists {} but no issue file exists".format(extra))
            for iid in sorted(set(rows) & set(by_id), key=id_num):
                want = status_display(by_id[iid]["fields"].get("Status", ""))
                got = rows[iid][2] if len(rows[iid]) > 2 else ""
                if status_base(got) != status_base(want):
                    errors.append("audit/REPORT.md: {} status '{}' but issue file says '{}'".format(iid, got, want))
            expected = counts(issues)
            if counts_line != expected:
                errors.append("audit/REPORT.md: counts line is stale\n    have: {}\n    want: {}".format(counts_line, expected))
    else:
        errors.append("audit/REPORT.md is missing")

    line_cache = {}
    md_files = [os.path.join(audit_dir, f) for f in sorted(os.listdir(audit_dir)) if f.endswith(".md")]
    md_files += [i["path"] for i in issues]
    closed = {i["path"] for i in issues
              if status_base(i["fields"].get("Status", "")) in ("Resolved", "Rejected", "Superseded")}
    for md in md_files:
        rel_md = os.path.relpath(md, root)
        # Closed issues cite evidence from the revision they were closed at;
        # later refactors may move those lines, so drift there is only a warning.
        report_link = warnings.append if md in closed else errors.append
        for n, target in md_links(md):
            if re.match(r"^[a-z][a-z0-9+.-]*:", target, re.I) or target.startswith("#"):
                continue
            path_part, _, anchor = target.partition("#")
            if not path_part:
                continue
            if path_part.startswith("/"):
                resolved = os.path.normpath(os.path.join(root, path_part.lstrip("/")))
            else:
                resolved = os.path.normpath(os.path.join(os.path.dirname(md), path_part))
            where = "{}:{}".format(rel_md, n)
            if not os.path.exists(resolved):
                report_link("{}: broken link {}".format(where, target))
                continue
            if os.path.isdir(resolved):
                warnings.append("{}: link to a directory {}".format(where, target))
                continue
            am = ANCHOR_RE.match(anchor) if anchor else None
            if am:
                if resolved not in line_cache:
                    try:
                        with open(resolved, "rb") as fh:
                            line_cache[resolved] = sum(1 for _ in fh)
                    except OSError:
                        line_cache[resolved] = 0
                last = int(am.group(2) or am.group(1))
                if last > line_cache[resolved]:
                    report_link("{}: anchor {} beyond end of {} ({} lines)".format(where, "#" + anchor, path_part, line_cache[resolved]))
            if not path_part.startswith("/") and not path_part.startswith("."):
                warnings.append("{}: relative link {} (contract uses /repo-root paths)".format(where, target))

    for w in warnings:
        print("warning: " + w)
    for e in errors:
        print("error: " + e)
    print("checked {} issue files, {} markdown files: {} errors, {} warnings".format(
        len(issues), len(md_files), len(errors), len(warnings)))
    return 1 if errors else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", help="repository root (default: git toplevel of the cwd)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check")
    rb = sub.add_parser("rebuild")
    rb.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    root = repo_root(args.repo)
    if args.cmd == "check":
        return check(root)
    return rebuild(root, args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
