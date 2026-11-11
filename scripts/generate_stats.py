#!/usr/bin/env python3
"""Generates assets/stats.svg, assets/languages.svg and assets/activity.svg
from the GitHub GraphQL API. Run by .github/workflows/stats.yml.

Usage:
  GH_TOKEN=... python scripts/generate_stats.py <username>
  python scripts/generate_stats.py --placeholder
  python scripts/generate_stats.py --mock          (local preview with fake data)
"""
import json, os, sys, urllib.request
from xml.sax.saxutils import escape

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")
FONT = "'Fira Code','JetBrains Mono','Cascadia Code',Consolas,'SF Mono',Menlo,'Courier New',monospace"

QUERY = """
query($login:String!){
  user(login:$login){
    followers{totalCount}
    repositories(ownerAffiliations:OWNER,isFork:false,first:100,orderBy:{field:PUSHED_AT,direction:DESC}){
      totalCount
      nodes{ stargazerCount languages(first:8,orderBy:{field:SIZE,direction:DESC}){ edges{ size node{ name } } } }
    }
    contributionsCollection{
      totalCommitContributions totalPullRequestContributions totalIssueContributions
      contributionCalendar{ totalContributions weeks{ contributionDays{ date contributionCount } } }
    }
  }
}"""

def fetch(login):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": login}}).encode(),
        headers={"Authorization": "bearer " + os.environ["GH_TOKEN"], "Content-Type": "application/json", "User-Agent": "profile-stats"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    if "errors" in data or not data.get("data", {}).get("user"):
        raise SystemExit("GitHub API error: " + json.dumps(data.get("errors", data))[:400])
    return data["data"]["user"]

def mock():
    import random
    random.seed(3)
    days = [{"date": f"d{i}", "contributionCount": random.choice([0, 0, 1, 2, 3, 5, 8, 12])} for i in range(371)]
    weeks = [{"contributionDays": days[i:i + 7]} for i in range(0, 371, 7)]
    langs = lambda *p: {"edges": [{"size": s, "node": {"name": n}} for n, s in p]}
    return {
        "followers": {"totalCount": 12},
        "repositories": {"totalCount": 18, "nodes": [
            {"stargazerCount": 4, "languages": langs(("JavaScript", 52000), ("HTML", 30000), ("CSS", 21000))},
            {"stargazerCount": 2, "languages": langs(("Python", 40000), ("JavaScript", 9000))},
            {"stargazerCount": 0, "languages": langs(("TypeScript", 25000), ("C++", 6000))}]},
        "contributionsCollection": {"totalCommitContributions": 61, "totalPullRequestContributions": 5, "totalIssueContributions": 2,
                                    "contributionCalendar": {"totalContributions": 70, "weeks": weeks}},
    }

def svg(w, h, body, defs=""):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img">'
            f'<defs>{defs}</defs><style>text{{font-family:{FONT};}}</style>'
            f'<rect width="{w}" height="{h}" rx="14" fill="#000"/>{body}</svg>')

def header(label, w):
    return (f'<text x="28" y="40" font-size="14" fill="#fff" letter-spacing="4" font-weight="700">{label}</text>'
            f'<rect x="28" y="52" width="{w-56}" height="1" fill="#222"/>'
            f'<rect y="51.5" width="70" height="2" fill="#fff"><animate attributeName="x" values="28;{w-98};28" dur="5s" repeatCount="indefinite"/></rect>')

def write(name, content):
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
        f.write(content)

def fmt(n):
    return f"{n/1000:.1f}k" if n >= 10000 else f"{n:,}"

def stats_card(u):
    c = u["contributionsCollection"]
    stars = sum(r["stargazerCount"] for r in u["repositories"]["nodes"])
    items = [("CONTRIBUTIONS", c["contributionCalendar"]["totalContributions"]), ("COMMITS", c["totalCommitContributions"]),
             ("PULL REQUESTS", c["totalPullRequestContributions"]), ("ISSUES", c["totalIssueContributions"]),
             ("STARS", stars), ("REPOSITORIES", u["repositories"]["totalCount"])]
    body = header("GITHUB STATS", 490)
    for i, (label, val) in enumerate(items):
        col, row = i % 2, i // 2
        x, y = 28 + col * 222, 74 + row * 72
        d = 0.2 + i * 0.25
        body += (f'<g opacity="0"><animate attributeName="opacity" values="0;1" dur="0.6s" begin="{d}s" fill="freeze"/>'
                 f'<animateTransform attributeName="transform" type="translate" values="0 14;0 0" dur="0.6s" begin="{d}s" fill="freeze"/>'
                 f'<rect x="{x}" y="{y}" width="208" height="60" rx="8" fill="#0a0a0a" stroke="#222"/>'
                 f'<text x="{x+16}" y="{y+37}" font-size="26" font-weight="700" fill="#fff">{fmt(val)}</text>'
                 f'<text x="{x+192}" y="{y+36}" text-anchor="end" font-size="10" fill="#777" letter-spacing="2">{label}</text></g>')
    return svg(490, 300, body)

def languages_card(u):
    totals = {}
    for r in u["repositories"]["nodes"]:
        for e in r["languages"]["edges"]:
            totals[e["node"]["name"]] = totals.get(e["node"]["name"], 0) + e["size"]
    top = sorted(totals.items(), key=lambda kv: -kv[1])[:6]
    s = sum(v for _, v in top) or 1
    body = header("TOP LANGUAGES", 490)
    if not top:
        body += '<text x="28" y="95" font-size="13" fill="#777">No language data yet.</text>'
    for i, (name, v) in enumerate(top):
        y = 76 + i * 36; pct = v / s * 100; bw = max(4, (490 - 56 - 90) * pct / 100); d = 0.2 + i * 0.25
        body += (f'<text x="28" y="{y+10}" font-size="13" fill="#e6e6e6">{escape(name)}</text>'
                 f'<text x="462" y="{y+10}" text-anchor="end" font-size="12" fill="#888">{pct:.1f}%</text>'
                 f'<rect x="28" y="{y+18}" width="434" height="5" rx="2.5" fill="#161616"/>'
                 f'<rect x="28" y="{y+18}" width="0" height="5" rx="2.5" fill="#fff"><animate attributeName="width" values="0;{bw*434/(490-56-90):.1f}" dur="1.2s" begin="{d}s" fill="freeze" calcMode="spline" keyTimes="0;1" keySplines=".2 .8 .2 1"/></rect>')
    return svg(490, 300, body)

def activity_card(u):
    days = [d for w in u["contributionsCollection"]["contributionCalendar"]["weeks"] for d in w["contributionDays"]][-70:]
    mx = max([d["contributionCount"] for d in days] + [1])
    W, H = 1000, 220; x0, base, ch = 28, 180, 110; step = (W - 56) / len(days); bw = step * 0.62
    body = header("CONTRIBUTION ACTIVITY  /  LAST 70 DAYS", W)
    for i, d in enumerate(days):
        v = d["contributionCount"]; h = max(2, v / mx * ch); x = x0 + i * step; b = 0.2 + i * 0.03
        body += (f'<rect x="{x:.1f}" y="{base}" width="{bw:.1f}" height="0" rx="2" fill="#fff" opacity="{0.35 if v == 0 else 0.9}">'
                 f'<animate attributeName="height" values="0;{h:.1f}" dur="0.7s" begin="{b:.2f}s" fill="freeze"/>'
                 f'<animate attributeName="y" values="{base};{base-h:.1f}" dur="0.7s" begin="{b:.2f}s" fill="freeze"/></rect>')
    body += (f'<rect x="{x0}" y="{base+6}" width="{W-56}" height="1" fill="#222"/>'
             f'<text x="{x0}" y="{base+28}" font-size="11" fill="#666" letter-spacing="2">PEAK {mx} / DAY</text>'
             f'<text x="{W-x0}" y="{base+28}" text-anchor="end" font-size="11" fill="#666" letter-spacing="2">{sum(d["contributionCount"] for d in days)} CONTRIBUTIONS</text>')
    return svg(W, H, body)

def placeholder(label, w, h):
    body = (f'<text x="{w/2}" y="{h/2-4}" text-anchor="middle" font-size="14" fill="#9a9a9a" letter-spacing="4">{label}</text>'
            f'<text x="{w/2}" y="{h/2+20}" text-anchor="middle" font-size="11" fill="#555" letter-spacing="2">UPDATES ON FIRST WORKFLOW RUN</text>'
            f'<rect x="{w/2-60}" y="{h/2+34}" width="120" height="2" fill="#1c1c1c"/>'
            f'<rect x="{w/2-60}" y="{h/2+34}" width="30" height="2" fill="#fff"><animate attributeName="x" values="{w/2-60};{w/2+30};{w/2-60}" dur="2s" repeatCount="indefinite"/></rect>')
    return svg(w, h, body)

def main():
    a = sys.argv[1:]
    if a[:1] == ["--placeholder"]:
        write("stats.svg", placeholder("GITHUB STATS", 490, 300))
        write("languages.svg", placeholder("TOP LANGUAGES", 490, 300))
        write("activity.svg", placeholder("CONTRIBUTION ACTIVITY", 1000, 220))
        return
    u = mock() if a[:1] == ["--mock"] else fetch(a[0])
    write("stats.svg", stats_card(u)); write("languages.svg", languages_card(u)); write("activity.svg", activity_card(u))

if __name__ == "__main__":
    main()
