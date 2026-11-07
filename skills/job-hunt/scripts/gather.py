# Gathers public job postings into one JSON list. Add company board slugs to B as you discover them (see references/sources.md).
# Gather jobs from public feeds into one JSON list: source, company, title, location, url, date, text.
import json, re, sys, time, html, urllib.request, urllib.parse, xml.etree.ElementTree as ET
OUT = sys.argv[1]
def get(u, h=None):
    req = urllib.request.Request(u, headers={'User-Agent': 'job-search-script', **(h or {})})
    with urllib.request.urlopen(req, timeout=30) as r: return r.read()
def strip(s): return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', html.unescape(s or ''))))
rows, health = [], []
def add(src, company, title, loc, url, date, text): rows.append(dict(src=src, company=company, title=title, loc=loc or '', url=url, date=(date or '')[:10], text=text or ''))
B = {
 'ashby': ['se3','sensmore','applied','proxima-fusion','wayve','robco','sereact','isembard','the-exploration-company','coachhub careers','zoe','skydio','the-robotics-company','loki','clera','rivianvw.tech','120ft-factory','q','rerun','polars','metalbear'],
 'greenhouse': ['arxroboticsgmbh','tensordyne','agilerobotsse','grover','apaleo','catapultsports','ecosio','hudl','workato'],
 'greenhouse-eu': ['gropyus'],
 'lever': ['hypersonica-prod','q-ctrl','wingtra-2','anybotics','shieldai','field-ai','kepler'],
 'personio': ['wandelbots','deepdrive-gmbh','autonomous-teaming','mynaric','fruitcore-robotics-gmbh','reflex-aerospace-gmbh','contabo','dataciders'],
}
for ats, slugs in B.items():
    for s in slugs:
        q = urllib.parse.quote(s); n0 = len(rows)
        try:
            if ats == 'ashby':
                for j in json.loads(get(f'https://api.ashbyhq.com/posting-api/job-board/{q}'))['jobs']:
                    add('ashby:'+s, s, j.get('title'), j.get('location'), j.get('jobUrl'), j.get('publishedAt'), j.get('descriptionPlain') or strip(j.get('descriptionHtml')))
            elif ats.startswith('greenhouse'):
                host = 'boards-api.eu.greenhouse.io' if ats.endswith('eu') else 'boards-api.greenhouse.io'
                for j in json.loads(get(f'https://{host}/v1/boards/{q}/jobs?content=true'))['jobs']:
                    add('greenhouse:'+s, s, j['title'], (j.get('location') or {}).get('name'), j.get('absolute_url'), j.get('updated_at'), strip(j.get('content')))
            elif ats == 'lever':
                for j in json.loads(get(f'https://api.lever.co/v0/postings/{q}?mode=json')):
                    t = (j.get('descriptionPlain') or '') + ' ' + ' '.join(strip(l.get('content')) for l in j.get('lists', [])) + ' ' + (j.get('additionalPlain') or '')
                    add('lever:'+s, s, j['text'], (j.get('categories') or {}).get('location'), j.get('hostedUrl'), time.strftime('%Y-%m-%d', time.gmtime((j.get('createdAt') or 0)/1000)), t)
            else:
                x = ET.fromstring(get(f'https://{q}.jobs.personio.de/xml'))
                for p in x.iter('position'):
                    add('personio:'+s, s, p.findtext('name',''), p.findtext('office',''), f"https://{q}.jobs.personio.de/job/{p.findtext('id','')}", p.findtext('createdAt',''), strip(' '.join(v.text or '' for v in p.iter('value'))))
            health.append((ats, s, len(rows)-n0))
        except Exception as e: health.append((ats, s, 'ERR '+str(e)[:30]))
        time.sleep(1)
# Arbeitnow (DE/NL/CH/UK/FR)
for pg in range(1, 11):
    try:
        for j in json.loads(get(f'https://www.arbeitnow.com/api/job-board-api?page={pg}'))['data']:
            add('arbeitnow', j['company_name'], j['title'], j['location'] + (' (remote)' if j.get('remote') else ''), j['url'], time.strftime('%Y-%m-%d', time.gmtime(j['created_at'])), strip(j['description']))
    except Exception as e: health.append(('arbeitnow', pg, 'ERR '+str(e)[:30]))
    time.sleep(1)
# Let's Get Rusty (JSON-LD on each page; descriptions truncated, details fetched later)
for pg in range(1, 22):
    try:
        t = get(f'https://jobs.letsgetrusty.com/?page={pg}').decode('utf-8','replace')
        for blk in re.findall(r'<script type="application/ld\+json">(.*?)</script>', t, re.S):
            try: d = json.loads(blk)
            except Exception: continue
            for it in d.get('itemListElement') or []:
                j = it.get('item', {})
                if j.get('@type') == 'JobPosting':
                    add('letsgetrusty', (j.get('hiringOrganization') or {}).get('name',''), j.get('title',''), (j.get('jobLocation') or {}).get('address', {}).get('addressCountry',''), j.get('url',''), j.get('datePosted',''), j.get('description',''))
    except Exception as e: health.append(('lgr', pg, 'ERR '+str(e)[:30]))
    time.sleep(1)
# Sweden public employment service
for q in ['rust','backend','devops','platform engineer','laravel','php','react','typescript','fullstack','golang','kubernetes','embedded','robotics','python django']:
    try:
        d = json.loads(get('https://jobsearch.api.jobtechdev.se/search?' + urllib.parse.urlencode({'q': q, 'limit': 100, 'published-after': 43200}), {'accept':'application/json'}))
        for h in d.get('hits', []):
            add('platsbanken', (h.get('employer') or {}).get('name',''), h.get('headline',''), ((h.get('workplace_address') or {}).get('municipality') or '') + ', Sweden', h.get('webpage_url',''), h.get('publication_date'), (h.get('description') or {}).get('text',''))
    except Exception as e: health.append(('platsbanken', q, 'ERR '+str(e)[:30]))
    time.sleep(1)
# LaraJobs RSS
try:
    x = ET.fromstring(get('https://larajobs.com/feed'))
    ns = {'job': 'https://larajobs.com'}
    for it in x.iter('item'):
        add('larajobs', it.findtext('job:company', '', ns), it.findtext('title',''), it.findtext('job:location','',ns), it.findtext('link',''), it.findtext('pubDate',''), strip(it.findtext('description','')))
except Exception as e: health.append(('larajobs','feed','ERR '+str(e)[:30]))
# dedupe by url
seen = {}; [seen.setdefault(r['url'], r) for r in rows]
json.dump({'rows': list(seen.values()), 'health': health}, open(OUT, 'w'))
from collections import Counter
print(len(seen), 'unique jobs'); print(Counter(r['src'].split(':')[0] for r in seen.values()))
print('errors:', [h for h in health if not isinstance(h[2], int)])
