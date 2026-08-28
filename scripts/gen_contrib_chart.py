"""Generate a polished contribution bar chart SVG from GitHub GraphQL API."""
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
        totalContributions
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

def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def main():
    to = datetime.utcnow()
    frm = to - timedelta(days=30)
    data = gql(TOKEN, query, {"user": USERNAME, "from": frm.isoformat() + "Z", "to": to.isoformat() + "Z"})
    cc = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    weeks = cc["weeks"]
    total = cc["totalContributions"]
    days = []
    for w in weeks:
        for d in w["contributionDays"]:
            days.append((d["date"][:10], d["contributionCount"]))
    days = days[-30:]

    best = max(days, key=lambda x: x[1])
    active = sum(1 for _, c in days if c > 0)
    avg = total / len(days) if days else 0

    # Canvas
    W, H = 820, 240
    PAD = 28
    PAD_L, PAD_R = PAD + 8, PAD
    PAD_T, PAD_B = 76, 38
    chart_w = W - PAD_L - PAD_R
    chart_h = H - PAD_T - PAD_B
    max_c = max((c for _, c in days), default=1) or 1
    n = len(days)
    slot = chart_w / n
    bar_w = slot * 0.62

    # Grid lines (4 evenly spaced)
    grid = []
    for i in range(1, 5):
        gy = PAD_T + chart_h - (chart_h / 4 * i)
        grid.append(f'<line x1="{PAD_L}" y1="{gy:.1f}" x2="{W - PAD_R}" y2="{gy:.1f}" stroke="#E1E4E8" stroke-width="0.5" stroke-dasharray="3,3"/>')

    # Bars with gradient + rounded top
    defs = f'''<defs>
    <linearGradient id="barGrad" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#58A6FF"/>
      <stop offset="100%" stop-color="#0969DA"/>
    </linearGradient>
    <linearGradient id="barGradIdle" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#21262D"/>
      <stop offset="100%" stop-color="#161B22"/>
    </linearGradient>
  </defs>'''

    bars = []
    for i, (date, count) in enumerate(days):
        x = PAD_L + i * slot + (slot - bar_w) / 2
        if count > 0:
            h = max((count / max_c) * chart_h, 4)
            y = PAD_T + chart_h - h
            bars.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{h:.1f}" rx="3" fill="url(#barGrad)"/>')
            if count >= max_c * 0.5:
                bars.append(f'<text x="{x + bar_w/2:.1f}" y="{y - 6:.1f}" text-anchor="middle" fill="#79C0FF" font-size="9.5" font-weight="500" font-family="ui-monospace,monospace">{count}</text>')
        else:
            bars.append(f'<rect x="{x:.1f}" y="{PAD_T + chart_h - 2:.1f}" width="{bar_w:.1f}" height="2" rx="1" fill="#D0D7DE"/>')
        if i % 5 == 0:
            label = date[5:]
            bars.append(f'<text x="{x + bar_w/2:.1f}" y="{H - 12}" text-anchor="middle" fill="#57606A" font-size="9" font-family="ui-monospace,monospace">{label}</text>')

    # Summary pills
    def pill(x, y, w, label, value):
        return (f'<rect x="{x}" y="{y}" width="{w}" height="28" rx="6" fill="#F6F8FA" stroke="#D0D7DE" stroke-width="1"/>'
                f'<text x="{x + 10}" y="{y + 18}" fill="#57606A" font-size="10" font-family="-apple-system,sans-serif">{esc(label)}</text>'
                f'<text x="{x + w - 10}" y="{y + 18}" text-anchor="end" fill="#24292F" font-size="11" font-weight="600" font-family="ui-monospace,monospace">{esc(value)}</text>')

    pill_w = 120
    pill_gap = 12
    pills_y = 14
    p1 = pill(PAD_L, pills_y, pill_w, "Total", str(total))
    p2 = pill(PAD_L + pill_w + pill_gap, pills_y, pill_w, "Daily avg", f"{avg:.1f}")
    p3 = pill(PAD_L + 2 * (pill_w + pill_gap), pills_y, pill_w, "Best day", str(best[1]))
    p4 = pill(PAD_L + 3 * (pill_w + pill_gap), pills_y, pill_w, "Active days", f"{active}/{len(days)}")

    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
        f'<rect width="{W}" height="{H}" fill="#FFFFFF" rx="8"/>',
        f'<defs>{defs}</defs>',
        "".join(grid),
        f'<text x="{PAD_L}" y="{PAD_T - 12}" fill="#24292F" font-size="13" font-weight="600" font-family="-apple-system,BlinkMacSystemFont,sans-serif">Contributions</text>',
        f'<text x="{W - PAD_R}" y="{PAD_T - 12}" text-anchor="end" fill="#57606A" font-size="10" font-family="-apple-system,sans-serif">{frm.strftime("%b %d")} - {to.strftime("%b %d, %Y")}</text>',
        p1, p2, p3, p4,
        f'<line x1="{PAD_L}" y1="{PAD_T + chart_h}" x2="{W - PAD_R}" y2="{PAD_T + chart_h}" stroke="#30363D" stroke-width="1"/>',
        "\n".join(bars),
        '</svg>'
    ]

    svg = "\n".join(svg_parts)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        f.write(svg)
    print(f"generated {OUT}: {total} total, {avg:.1f} avg, best={best[1]}, active={active}/{len(days)}")

if __name__ == "__main__":
    main()
