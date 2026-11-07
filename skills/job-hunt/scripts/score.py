# Scores gathered jobs per track against the user's CVs. Adapt TRACK keywords, W weights, filters and DEFENCE_BONUS to the user (see references/scoring.md).
import json, re, sys
rows = json.load(open(sys.argv[1]))['rows']; OUT = sys.argv[2]
I = re.I
def has(p, t): return bool(re.search(p, t, I))
EU = r'german|deutschland|munich|münchen|berlin|stuttgart|hamburg|frankfurt|cologne|köln|nuremberg|nürnberg|erlangen|dresden|karlsruhe|leipzig|bremen|metzingen|riederich|gilching|ottobrunn|aachen|düsseldorf|hannover|regensburg|augsburg|sweden|stockholm|gothenburg|göteborg|malmö|linköping|uppsala|västerås|lund|jönköping|sundbyberg|solna|netherlands|amsterdam|eindhoven|delft|rotterdam|utrecht|switzerland|zurich|zürich|austria|vienna|wien|denmark|copenhagen|norway|oslo|finland|helsinki|estonia|tallinn|poland|warsaw|krak|wroc|ireland|dublin|spain|madrid|barcelona|portugal|lisbon|porto|belgium|europe|emea|\beu\b|czech|prague'
DE = r'german|deutschland|\bde\b|munich|münchen|berlin|stuttgart|hamburg|frankfurt|cologne|köln|nuremberg|nürnberg|fürth|erlangen|dresden|karlsruhe|leipzig|bremen|metzingen|riederich|gilching|wessling|weßling|garching|freising|ottobrunn|parsdorf|ingolstadt|aachen|düsseldorf|hannover|hanover|regensburg|augsburg|darmstadt|rostock|cottbus|rödental|dingolfing|mainz|bonn|mannheim|heidelberg|wiesbaden|kassel|münster|essen|dortmund|bochum|freiburg|ulm|würzburg|kiel|lübeck|potsdam|jena|magdeburg|bielefeld|paderborn|wolfsburg|braunschweig|göttingen|oldenburg|osnabrück|saarbrücken|koblenz|siegen|passau|bamberg|bayreuth|mainburg|standort'
SE = r'sweden|stockholm|gothenburg|göteborg|malmö|linköping|uppsala|västerås|lund|jönköping|sundbyberg|solna|norrköping|örebro|umeå|eskilstuna'
EUR = r'netherlands|nederland|amsterdam|eindhoven|delft|rotterdam|utrecht|assen|groningen|switzerland|schweiz|zurich|zürich|bern|basel|lausanne|geneva|lucerne|luzern|schlieren|thun|st\.? gallen|austria|vienna|wien|linz|graz|denmark|copenhagen|norway|oslo|finland|helsinki|espoo|estonia|tallinn|poland|warsaw|krak|wroc|gdansk|poznan|ireland|dublin|spain|madrid|barcelona|portugal|lisbon|porto|belgium|brussels|europe|emea|\beu\b|czech|prague|brno|united kingdom|\buk\b|england|scotland|london|manchester|edinburgh|glasgow|bristol|cambridge|oxford|france|paris|toulouse|lyon|lille|nantes|bordeaux|italy|milan|rome|turin|chiavari|hungary|budapest|romania|bucharest|croatia|serbia|belgrade|greece|athens|slovenia|slovakia|bulgaria|lithuania|latvia|cyprus|luxembourg'
NA = r'united states|usa|\bus\b|california|new york|texas|washington|massachusetts|boston|seattle|sunnyvale|san francisco|san mateo|palo alto|irvine|ann arbor|los angeles|austin|denver|pittsburgh|florida|\bfl\b|\bca\b|canada|toronto|vancouver|montreal|ontario|british columbia|ottawa|waterloo'
REMOTE_ANY = r'^remote$|work from anywhere|worldwide|anywhere in the world'
STUDENT = r'intern\b|internship|working student|werkstudent|praktik|thesis|abschlussarbeit|trainee|apprentice|ausbildung|student|phd'
TOP = r'\b(staff|principal|lead|head|director|manager|vp|chief|cto|architect)\b'
GERMAN_REQ = r'(fluency in german|german (language )?skills (are )?(required|essential)|fließend|verhandlungssicher|sehr gute[n]? deutsch|gute[n]? deutsch|deutschkenntnisse|german (language )?(is )?(required|mandatory|essential)|fluent (in )?german|native german|german (at )?c1|c1.{0,20}german|business.fluent german)'
SWEDISH_REQ = r'(fluent|native|professional).{0,20}swedish|swedish.{0,25}(required|is a must|mandatory)|svenska (är|krav)|talar och skriver svenska'
CPP_FIRST = r'(strong|expert|excellent|solid|proficien)\w*.{0,40}\b(C\+\+|C/C\+\+|modern C\+\+)|\bC\+\+(1[47]|20)\b'
NO_SPONSOR = r'sponsorship is not (available|offered|possible)|not (able|in a position) to (offer|provide) (visa )?sponsorship|must (reside|be based|live) in|eligible to work in \w+ without (visa )?sponsorship|without (the need for )?(visa )?sponsorship|already (have|hold) (a )?(valid )?work permit|right to work in the (eu|uk|us)|must (already )?(have|hold) (the )?right to work|no visa sponsorship|cannot sponsor|unable to sponsor|not able to sponsor'
LEGAL = r'(eu|eea|german|us|u\.s\.|british|uk|swedish|dutch) (citizen|citizenship|national)|security clearance|sicherheitsüberprüfung|\bü[23]\b|\bitar\b|export control.{0,40}(citizen|person)'
VISA = r'visa sponsor|sponsor (your |a )?visa|relocation (support|assistance|package|budget)|we (can |will )?(help|support) (you )?(with )?(relocat|visa)'
def years(t):
    ys = [int(m.group(1)) for m in re.finditer(r'(\d{1,2})\s*\+?\s*(?:-|–|to)?\s*\d{0,2}\+?\s*(?:years|yrs|jahre|år)', t, I) if int(m.group(1)) < 20]
    return min(ys) if ys else None
def track(r):
    t, d = r['title'], r['text'][:4000]
    if has(r'\brust\b', t) or (has(r'\brust\b', d) and (len(re.findall(r'\brust\b', d, I)) >= 2) and not has(r'\b(php|java|\.net|c#)\b', t)): return 'rust'
    if has(r'devops|\bsre\b|site reliability|platform engineer|infrastructure engineer|cloud engineer|cloud infrastructure|kubernetes|release engineer|ops engineer', t): return 'devops'
    if has(r'backend|back-end|frontend|front-end|full.?stack|fullstack|web developer|software engineer|software developer|product engineer|php|laravel|django|react|next\.?js|typescript|node', t) and not has(r'embedded|firmware|android|ios\b|mobile|data scien|machine learning|\bml\b|qa\b|test', t): return 'web'
    return None
W = {
 'web': [(r'laravel', 12), (r'\bphp\b', 8), (r'django', 7), (r'\bpython\b', 4), (r'react', 7), (r'next\.?js', 5), (r'typescript', 5), (r'postgres', 3), (r'redis', 2), (r'docker', 2), (r'websocket', 2), (r'oauth|authentication|identity', 2), (r'typesense|elastic', 1), (r'react native', 2)],
 'devops': [(r'docker', 5), (r'kubernetes|k8s|k3s', 5), (r'ansible', 7), (r'ci/cd|github actions|gitlab', 4), (r'linux', 3), (r'traefik|nginx', 4), (r'postgres', 2), (r'hetzner|bare.?metal|on.?prem', 2), (r'helm', 2), (r'python|bash', 2), (r'terraform|opentofu', 1), (r'aws|gcp|azure', 1)],
 'rust': [(r'\brust\b', 12), (r'tokio|async', 4), (r'axum|actix', 4), (r'postgres|sqlx', 2), (r'\bros ?2?\b', 5), (r'embedded-hal|no_std|embassy|rtic|probe-rs', 7), (r'embedded|firmware', 3), (r'robot|autonom|drone|uav', 4), (r'webassembly|wasm|leptos', 3), (r'docker|kubernetes', 2), (r'slam|kalman|ekf|path planning', 3)],
}
out = []
for r in rows:
    tr = track(r)
    if not tr: continue
    t, d, loc = r['title'], r['text'], r['loc']
    full = t + ' ' + d
    flags, gate = [], None
    L = loc + ' ' + ('sweden' if r['src']=='platsbanken' else '') + (' deutschland' if r['src']=='arbeitnow' and '://www.arbeitnow.com/' in r['url'] and not has(r'remote', loc) else '') + (' deutschland' if r['src'].startswith('personio') else '')
    region = 'DE' if has(DE, L) else 'SE' if has(SE, L) else 'EU' if has(EUR, L) else 'NA' if has(NA, L) else 'remote' if has(r'remote|anywhere|worldwide', L) else 'other'
    if has(STUDENT, t): gate = 'student'
    if has(TOP, t): gate = 'level-top'
    if has(GERMAN_REQ, d): gate = gate or 'german'
    if has(SWEDISH_REQ, d): gate = gate or 'swedish'
    if r['src'] == 'platsbanken':
        w = re.findall(r'[a-zåäö]+', d.lower())
        if sum(x in {'och','att','du','med','vi','för','som','av','har','erfarenhet'} for x in w) > sum(x in {'the','and','you','with','our','will','experience','we','for','of'} for x in w): gate = gate or 'swedish-ad'
    if r['src'] == 'arbeitnow' and has(r'(m/w/d|w/m/d|\(w/m|entwickler|ingenieur)', t) and not has(r'\b(the|and|with|you)\b', d[:400]): gate = gate or 'german-ad'
    if tr == 'rust' and has(CPP_FIRST, d) and len(re.findall(r'\brust\b', d, I)) < 3: gate = gate or 'cpp-first'
    if tr == 'web' and has(r'\b(java|spring|\.net|c#|kotlin|ruby|rails|angular|vue)\b', t): gate = gate or 'stack'
    if has(r'\bjunior\b|graduate|entry', t) and tr in ('web', 'devops'): gate = gate or 'level-junior'
    y = years(d)
    if y is not None and ((tr == 'web' and y > 8) or (tr == 'devops' and y > 6) or (tr == 'rust' and y > 7)): gate = gate or f'years>{y}'
    if has(NO_SPONSOR, d): flags.append('no-sponsorship-stated')
    if has(LEGAL, d) and not has(r'nato', d): gate = gate or 'citizenship/clearance'
    if has(r'nato', d) and has(LEGAL, d): flags.append('NATO citizens accepted (Albania is NATO)')
    pos = [m for m in re.finditer(r'[^.\n]*(?:' + VISA + r')[^.\n]*', full, I) if not re.search(r'\bnot\b|\bno\b|cannot|unable', m.group(0), I)]
    if pos: flags.append('visa/relocation')
    if has(r'defen[cs]e|military|counter-?drone|munition|interceptor', full): flags.append('defence')
    if has(r'recruit|staffing|personal(dienst|vermittlung)|consulting group|talent partners', r['company']): flags.append('agency?')
    s = sum(w for p, w in W[tr] if has(p, full))
    s = min(s, 40)
    lvl = 15 if y is None or (tr=='web' and 2 <= y <= 6) or (tr=='devops' and 2 <= y <= 5) or (tr=='rust' and y <= 5) else 8
    if tr == 'rust' and has(r'robot|embedded|firmware|drone', full) and has(r'senior|sr\.', t): lvl = 6
    if tr in ('web','devops') and has(r'senior', t): lvl = min(lvl, 12) if y is None or y <= 6 else 6
    loc_pts = {'DE': 12, 'SE': 11, 'EU': 8, 'remote': 7, 'NA': 5, 'other': 3}[region]
    lang = 10 if not has(r'deutsch|german', d) else 7
    vis = 8 if 'visa/relocation' in flags else 0
    pen = -8 if 'no-sponsorship-stated' in flags else 0
    DEFENCE_BONUS = 4  # user prefers defence/dual-use (preferences.md); set to 0 or negative for other users
    dfn = DEFENCE_BONUS if 'defence' in flags else 0
    score = round(min(100, s * 1.4 + lvl + loc_pts + lang + vis + pen + dfn))
    out.append(dict(track=tr, score=score, gate=gate, flags=flags, years=y, region=region, **{k: r[k] for k in ('src','company','title','loc','url','date')}, snippet=d[:300]))
best = {}
for o in out:
    k = (o['track'], o['company'].lower().strip(), re.sub(r'\s+', ' ', o['title'].lower().strip()))
    if k not in best or (o['gate'] is None, o['score']) > (best[k]['gate'] is None, best[k]['score']):
        o['also'] = (best[k].get('also', []) + [best[k]['loc']]) if k in best else []
        best[k] = o
    else: best[k].setdefault('also', []).append(o['loc'])
out = list(best.values())
json.dump(out, open(OUT, 'w'))
from collections import Counter
print(Counter((o['track'], o['gate'] is None) for o in out))
print(Counter(o['gate'] for o in out if o['gate']).most_common(12))
for tr in ('web','devops','rust'):
    ok = sorted([o for o in out if o['track']==tr and not o['gate']], key=lambda o: -o['score'])
    print(f'\n=== {tr}: {len(ok)} pass gates; top 30')
    for o in ok[:30]: print(f"{o['score']:3} | {o['date']} | {o['title'][:55]} | {o['company'][:22]} | {o['loc'][:28]} | y={o['years']} | {','.join(o['flags'])} | {o['src'][:12]}")
