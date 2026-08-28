"""Generate a flat contribution bar chart SVG from GitHub GraphQL API."""
import json, os, urllib.request
from datetime import datetime, timedelta

TOKEN = os.environ.get("GITHUB_TOKEN", "")
USERNAME = os.environ.get("USERNAME", "Apageoflove")
OUT = "assets/contrib_chart.svg"

query = """
query($user: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $user) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}"""

def gql(token, q, variables):
    req = urllib.request.Request("https://api.github.com/graphql",
        data=json.dumps({"query": q, "variables": variables}).encode(),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())

def main():
    to = datetime.utcnow()
    frm = to - timedelta(days=30)
    data = gql(TOKEN, query, {"user": USERNAME, "from": frm.isoformat() + "Z", "to": to.isoformat() + "Z"})
    weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    days = []
    for w in weeks:
        for d in w["contributionDays"]:
            days.append((d["date"][:10], d["contributionCount"]))
    days = days[-30:]

    W, H = 800, 220
    PAD_L, PAD_R, PAD_T, PAD_B = 40, 20, 40, 35
    chart_w = W - PAD_L - PAD_R
    chart_h = H - PAD_T - PAD_B
    max_c = max((c for _, c in days), default=1) or 1
    n = len(days)
    bar_w = chart_w / n * 0.65
    gap = chart_w / n * 0.35

    bars = []
    for i, (date, count) in enumerate(days):
        h = (count / max_c) * chart_h if count > 0 else 2
        x = PAD_L + i * (bar_w + gap) + gap / 2
        y = PAD_T + chart_h - h
        color = "#58A6FF" if count > 0 else "#21262D"
        bars.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{h:.1f}" fill="{color}" rx="2"/>')
        if count > 0:
            bars.append(f'<text x="{x + bar_w/2:.1f}" y="{y - 5:.1f}" text-anchor="middle" fill="#8B949E" font-size="9" font-family="monospace">{count}</text>')
        if i % 5 == 0:
            label = date[5:]
            bars.append(f'<text x="{x + bar_w/2:.1f}" y="{H - 10}" text-anchor="middle" fill="#8B949E" font-size="9" font-family="monospace">{label}</text>')

    total = sum(c for _, c in days)
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">\n'
    svg += f'<rect width="{W}" height="{H}" fill="#0D1117" rx="6"/>\n'
    svg += f'<text x="{PAD_L}" y="25" fill="#C9D1D9" font-size="14" font-weight="bold" font-family="-apple-system,sans-serif">Contributions - last 30 days (total: {total})</text>\n'
    svg += f'<line x1="{PAD_L}" y1="{PAD_T + chart_h}" x2="{W - PAD_R}" y2="{PAD_T + chart_h}" stroke="#30363D" stroke-width="1"/>\n'
    svg += "\n".join(bars) + "\n</svg>"

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        f.write(svg)
    print(f"generated {OUT}: {total} contributions in last {n} days")

if __name__ == "__main__":
    main()
