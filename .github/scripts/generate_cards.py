"""Generate profile stat cards (cards/stats.svg, cards/languages.svg) from the GitHub GraphQL API."""
import json, math, os, sys, urllib.request
from datetime import datetime, timezone

USER = os.environ.get("GH_USER", "c0mpuTurtle")
TOKEN = os.environ["GITHUB_TOKEN"]
OUT = os.environ.get("OUT_DIR", "cards")

BG, BD, TITLE, TXT, SUB = "#0d1117", "#30363d", "#58a6ff", "#c9d1d9", "#8b949e"
FONT = "font-family=\"'Segoe UI', Ubuntu, 'Helvetica Neue', sans-serif\""
LANG_COLORS = {"Java": "#F89820", "Python": "#FFD43B", "TypeScript": "#3178C6",
               "JavaScript": "#F1E05A", "Kotlin": "#A97BFF", "HTML": "#E34C26",
               "CSS": "#2DBA4E", "Shell": "#89E051", "Go": "#00ADD8", "C++": "#F34B7D"}
FALLBACK = ["#E06C75", "#56B6C2", "#C678DD", "#98C379", "#D19A66"]


def gql(query, variables=None):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables or {}}).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        body = json.load(r)
    if body.get("errors"):
        sys.exit(f"GraphQL error: {body['errors']}")
    return body["data"]


base = gql("""query($login:String!){ user(login:$login){
  createdAt
  pullRequests{ totalCount }
  issues{ totalCount }
  repositoriesContributedTo(contributionTypes:[COMMIT,ISSUE,PULL_REQUEST,REPOSITORY]){ totalCount }
}}""", {"login": USER})["user"]

YEAR_Q = """query($login:String!,$from:DateTime!,$to:DateTime!){ user(login:$login){
  contributionsCollection(from:$from,to:$to){
    totalCommitContributions
    commitContributionsByRepository(maxRepositories:100){
      repository{ primaryLanguage{ name } }
      contributions{ totalCount }
    }
  }
}}"""

now = datetime.now(timezone.utc)
total_commits, langs = 0, {}
for year in range(int(base["createdAt"][:4]), now.year + 1):
    frm = f"{year}-01-01T00:00:00Z"
    to = now.strftime("%Y-%m-%dT%H:%M:%SZ") if year == now.year else f"{year}-12-31T23:59:59Z"
    cc = gql(YEAR_Q, {"login": USER, "from": frm, "to": to})["user"]["contributionsCollection"]
    total_commits += cc["totalCommitContributions"]
    for item in cc["commitContributionsByRepository"]:
        lang = item["repository"]["primaryLanguage"]
        if lang:
            langs[lang["name"]] = langs.get(lang["name"], 0) + item["contributions"]["totalCount"]

stats = [("Total Commits", total_commits), ("Total PRs", base["pullRequests"]["totalCount"]),
         ("Total Issues", base["issues"]["totalCount"]),
         ("Contributed to", base["repositoriesContributedTo"]["totalCount"])]
print("stats:", stats, "langs:", langs)

from card_icons import ICONS


def card(title, size=22):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="340" height="200" viewBox="0 0 340 200" {FONT}>\n'
            f'<rect x="0.5" y="0.5" width="339" height="199" rx="4.5" fill="{BG}" stroke="{BD}"/>\n'
            f'<text x="30" y="40" font-size="{size}" fill="{TITLE}">{title}</text>\n')


s = card("Stats")
for i, ((label, value), icon) in enumerate(zip(stats, ICONS)):
    y = 75 + i * 28
    s += (f'<g transform="translate(30,{y - 12})"><path fill="{SUB}" d="{icon}"/></g>\n'
          f'<text x="54" y="{y}" font-size="14" fill="{TXT}">{label}</text>\n'
          f'<text x="200" y="{y}" font-size="15" font-weight="600" fill="{TXT}">{value:,}</text>\n')
s += (f'<g transform="translate(275,105)"><circle r="38" fill="none" stroke="{TITLE}" stroke-width="3" opacity="0.9"/>'
      f'<text y="7" text-anchor="middle" font-size="20" fill="{TITLE}">&#x1F422;</text></g>\n</svg>\n')

top = sorted(langs.items(), key=lambda kv: -kv[1])[:5]
total = sum(v for _, v in top) or 1
L = card("Top Languages by Commit", 20)
cx, cy, R, r = 262, 122, 52, 33
a0, fb = 0.0, iter(FALLBACK)
rows_y0 = 92 if len(top) <= 3 else 72
for i, (name, count) in enumerate(top):
    pct = count / total
    color = LANG_COLORS.get(name) or next(fb)
    a1 = a0 + pct * 2 * math.pi
    if pct >= 0.9999:
        L += (f'<circle cx="{cx}" cy="{cy}" r="{(R + r) / 2}" fill="none" stroke="{color}" stroke-width="{R - r}"/>\n')
    else:
        p = lambda rad, a: (cx + rad * math.sin(a), cy - rad * math.cos(a))
        (x0, y0), (x1, y1), (x2, y2), (x3, y3) = p(R, a0), p(R, a1), p(r, a1), p(r, a0)
        lg = 1 if a1 - a0 > math.pi else 0
        L += (f'<path fill="{color}" stroke="{BG}" stroke-width="1" d="M{x0:.2f},{y0:.2f}A{R},{R} 0 {lg} 1 {x1:.2f},{y1:.2f}'
              f'L{x2:.2f},{y2:.2f}A{r},{r} 0 {lg} 0 {x3:.2f},{y3:.2f}Z"/>\n')
    y = rows_y0 + i * 26
    L += (f'<rect x="30" y="{y - 11}" width="12" height="12" rx="2" fill="{color}"/>\n'
          f'<text x="50" y="{y}" font-size="14" fill="{TXT}">{name}</text>\n'
          f'<text x="140" y="{y}" font-size="14" fill="{SUB}">{pct * 100:.1f}%</text>\n')
    a0 = a1
L += "</svg>\n"

os.makedirs(OUT, exist_ok=True)
open(os.path.join(OUT, "stats.svg"), "w").write(s)
open(os.path.join(OUT, "languages.svg"), "w").write(L)
