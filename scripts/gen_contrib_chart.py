"""Generate an isometric 3D contribution bar chart SVG."""
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
    W, H = 820, 280
    PAD_L, PAD_R = 36, 36
    PAD_T, PAD_B = 76, 42
    chart_w = W - PAD_L - PAD_R
    chart_h = H - PAD_T - PAD_B
    max_c = max((c for _, c in days), default=1) or 1
    n = len(days)
    slot = chart_w / n
    bar_w = slot * 0.5      # narrower so the right face is visible

    # Isometric projection offsets (top-right of bar shifts up-right)
    iso_x = 9              # horizontal shift for top face
    iso_y = -7             # vertical shift for top face (up)

    # Grid lines (4 evenly spaced)
    grid = []
    for i in range(1, 5):
        gy = PAD_T + chart_h - (chart_h / 4 * i)
        grid.append(f'<line x1="{PAD_L}" y1="{gy:.1f}" x2="{W - PAD_R}" y2="{gy:.1f}" stroke="#E1E4E8" stroke-width="0.5" stroke-dasharray="3,3"/>')

    # 3D bar rendering: three faces per bar
    # Face colors by intensity
    def colors(count, is_best):
        if count == 0:
            return ('#EAEEF2', '#D8DEE4', '#EAEEF2')  # idle: nearly flat
        level = count / max_c
        if is_best or level >= 0.8:
            # Best/highlight: brighter blue
            base_top, base_right, base_front = '#A5D6FF', '#2188FF', '#0969DA'
        elif level >= 0.5:
            base_top, base_right, base_front = '#79B8FF', '#1F6FEB', '#0550AE'
        else:
            base_top, base_right, base_front = '#B6E3FF', '#58A6FF', '#2188FF'
        return (base_top, base_right, base_front)

    bars = []
    for i, (date, count) in enumerate(days):
        x = PAD_L + i * slot + (slot - bar_w) / 2
        baseline_y = PAD_T + chart_h
        is_best = (date == best[0] and count > 0)
        c_top, c_right, c_front = colors(count, is_best)

        if count > 0:
            h = max((count / max_c) * chart_h, 5)
            y_top = baseline_y - h
            # Front face (rectangle)
            bars.append(f'<path d="M{x:.1f},{y_top:.1f} L{x+bar_w:.1f},{y_top:.1f} L{x+bar_w:.1f},{baseline_y:.1f} L{x:.1f},{baseline_y:.1f} Z" fill="{c_front}"/>')
            # Right face (parallelogram going up-right)
            bars.append(f'<path d="M{x+bar_w:.1f},{y_top:.1f} L{x+bar_w+iso_x:.1f},{y_top+iso_y:.1f} L{x+bar_w+iso_x:.1f},{baseline_y+iso_y:.1f} L{x+bar_w:.1f},{baseline_y:.1f} Z" fill="{c_right}"/>')
            # Top face (parallelogram)
            bars.append(f'<path d="M{x:.1f},{y_top:.1f} L{x+iso_x:.1f},{y_top+iso_y:.1f} L{x+bar_w+iso_x:.1f},{y_top+iso_y:.1f} L{x+bar_w:.1f},{y_top:.1f} Z" fill="{c_top}" stroke="#FFFFFF" stroke-width="0.5"/>')
            # Value label above
            if count >= max_c * 0.5 or is_best:
                label_y = y_top + iso_y - 4
                bars.append(f'<text x="{x + bar_w/2 + iso_x/2:.1f}" y="{label_y:.1f}" text-anchor="middle" fill="#0969DA" font-size="9.5" font-weight="600" font-family="ui-monospace,monospace">{count}</text>')
        else:
            # Idle bar: just a small isometric platform
            bars.append(f'<path d="M{x:.1f},{baseline_y:.1f} L{x+iso_x:.1f},{baseline_y+iso_y:.1f} L{x+bar_w+iso_x:.1f},{baseline_y+iso_y:.1f} L{x+bar_w:.1f},{baseline_y:.1f} Z" fill="#D8DEE4" stroke="#FFFFFF" stroke-width="0.5"/>')

        # X-axis labels every 5 days
        if i % 5 == 0:
            label = date[5:]
            bars.append(f'<text x="{x + bar_w/2 + iso_x/2:.1f}" y="{baseline_y + iso_y + 14}" text-anchor="middle" fill="#57606A" font-size="9" font-family="ui-monospace,monospace">{label}</text>')

    # Baseline + isometric shadow strip (gives ground)
    base_y = PAD_T + chart_h
    ground = f'<line x1="{PAD_L}" y1="{base_y:.1f}" x2="{W - PAD_R}" y2="{base_y:.1f}" stroke="#D0D7DE" stroke-width="1"/>'
    # Subtle ground shadow under each bar (the isometric platform strip)
    shadow = []
    for i, (_, count) in enumerate(days):
        x = PAD_L + i * slot + (slot - bar_w) / 2
        if count == 0: continue
        shadow.append(f'<path d="M{x:.1f},{base_y+2:.1f} L{x+bar_w:.1f},{base_y+2:.1f} L{x+bar_w+iso_x:.1f},{base_y+2+iso_y:.1f} L{x+iso_x:.1f},{base_y+2+iso_y:.1f} Z" fill="#000000" opacity="0.04"/>')

    # Summary pills
    def pill(x, y, w, label, value):
        return (f'<rect x="{x}" y="{y}" width="{w}" height="28" rx="6" fill="#F6F8FA" stroke="#D0D7DE" stroke-width="1"/>'
                f'<text x="{x + 12}" y="{y + 18}" fill="#57606A" font-size="10.5" font-family="-apple-system,BlinkMacSystemFont,sans-serif">{esc(label)}</text>'
                f'<text x="{x + w - 12}" y="{y + 18}" text-anchor="end" fill="#24292F" font-size="11.5" font-weight="700" font-family="ui-monospace,monospace">{esc(value)}</text>')

    pill_w = 130
    pill_gap = 14
    pills_y = 22
    p1 = pill(PAD_L, pills_y, pill_w, "Total", str(total))
    p2 = pill(PAD_L + pill_w + pill_gap, pills_y, pill_w, "Daily avg", f"{avg:.1f}")
    p3 = pill(PAD_L + 2 * (pill_w + pill_gap), pills_y, pill_w, "Best day", str(best[1]))
    p4 = pill(PAD_L + 3 * (pill_w + pill_gap), pills_y, pill_w, "Active days", f"{active}/{len(days)}")

    # Title + date range
    title_y = 18
    # Empty defs block (no gradients; flat colors look cleaner for the isometric look)
    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
        f'<rect width="{W}" height="{H}" fill="#FFFFFF" rx="8"/>',
        f'<text x="{PAD_L}" y="{title_y}" fill="#24292F" font-size="13" font-weight="700" font-family="-apple-system,BlinkMacSystemFont,sans-serif">Contributions</text>',
        f'<text x="{W - PAD_R}" y="{title_y}" text-anchor="end" fill="#57606A" font-size="11" font-family="-apple-system,BlinkMacSystemFont,sans-serif">{frm.strftime("%b %d")} - {to.strftime("%b %d, %Y")}</text>',
        p1, p2, p3, p4,
        "".join(grid),
        "".join(shadow),
        ground,
        chr(10).join(bars),
        '</svg>'
    ]

    final = chr(10).join(svg_parts)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        f.write(final)
    print(f"generated {OUT}: {total} total, {avg:.1f} avg, best={best[1]}, active={active}/{len(days)}, size={len(final)}")

if __name__ == "__main__":
    main()
