"""Generate a soft isometric 3D contribution bar chart SVG.

Compared to v2, this version:
- Replaces the saturated GitHub blue palette with a softer indigo-blue
  monochrome ramp (lighter, more pastel).
- Adds subtle translucent strokes on each face to soften hard edges.
- Rounds the top corners of each bar (the seam where the three faces
  meet) with quadratic Bézier arcs so the silhouette is no longer sharp.
- Removes the per-height tier color swap in favor of an opacity ramp,
  which keeps the palette unified while still differentiating low /
  mid / peak days.
- Keeps the same canvas, pill row, and grid layout so the chart sits
  exactly where it did before; only the bar geometry and palette change.
"""
import json, os, urllib.request
from datetime import datetime, timedelta

TOKEN = os.environ.get("GITHUB_TOKEN", "")
USERNAME = os.environ.get("USERNAME", "Apageoflove")
OUT = "assets/contrib_chart.svg"

QUERY = """
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
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": q, "variables": variables}).encode(),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# Soft indigo-blue palette. Same hue across the three faces — only
# brightness (lightness) differs — so the chart reads as one object lit
# from the upper-right rather than three flat blue panels.
COL_TOP = "#E0E7FF"     # lightest, catches the most light
COL_RIGHT = "#A5B4FC"   # mid
COL_FRONT = "#6366F1"   # darkest, in shadow
COL_EDGE = "#6366F1"    # stroke (matches front face, looks intentional)
COL_GRID = "#EEF1F4"    # lighter, softer than before
COL_SHADOW = "#312E81"  # deep indigo for ground shadows


def bar_faces(x, baseline_y, bar_w, h, opacity, iso_x=8, iso_y=-6, r=2):
    """Three faces of an isometric 3D bar with rounded silhouette.

    - Front face: rectangle with both top corners rounded (r=2).
    - Right face: rectangle with the top corner rounded (the bar's
      outer edge from the light's point of view).
    - Top face: simple parallelogram. The three corners that touch
      the front or right face follow the arcs those faces have
      already drawn, so the silhouette as a whole reads as a single
      rounded bar even though the top face's own path is straight.
    """
    y_top = baseline_y - h
    # Front face: top corners arc, bottom corners square (they sit on
    # the baseline).
    front = (
        f"M{x+r:.2f},{y_top:.2f} "
        f"L{x+bar_w-r:.2f},{y_top:.2f} "
        f"Q{x+bar_w:.2f},{y_top:.2f} {x+bar_w:.2f},{y_top+r:.2f} "
        f"L{x+bar_w:.2f},{baseline_y:.2f} "
        f"L{x:.2f},{baseline_y:.2f} "
        f"L{x:.2f},{y_top+r:.2f} "
        f"Q{x:.2f},{y_top:.2f} {x+r:.2f},{y_top:.2f} Z"
    )
    # Right face: only the top corner (the bar's outer edge) is
    # rounded. The bottom corner sits on the baseline.
    rt_top_x = x + bar_w + iso_x
    rt_top_y = y_top + iso_y
    rb_top_x = x + bar_w
    rb_top_y = y_top
    rb_bot_x = x + bar_w
    rb_bot_y = baseline_y
    right = (
        f"M{rb_top_x:.2f},{rb_top_y+r:.2f} "
        f"Q{rb_top_x:.2f},{rb_top_y:.2f} {rb_top_x+r:.2f},{rb_top_y:.2f} "
        f"L{rt_top_x:.2f},{rt_top_y:.2f} "
        f"L{rt_top_x:.2f},{baseline_y+iso_y:.2f} "
        f"L{rb_bot_x:.2f},{rb_bot_y:.2f} Z"
    )
    # Top face: simple parallelogram. The corners already follow the
    # arcs on the front and right faces when rendered together, so no
    # extra arcs are needed here.
    tl_x, tl_y = x, y_top
    tr_x, tr_y = x + bar_w, y_top
    br_x, br_y = x + bar_w + iso_x, y_top + iso_y
    bl_x, bl_y = x + iso_x, y_top + iso_y
    top = (
        f"M{tl_x:.2f},{tl_y:.2f} "
        f"L{tr_x:.2f},{tr_y:.2f} "
        f"L{br_x:.2f},{br_y:.2f} "
        f"L{bl_x:.2f},{bl_y:.2f} Z"
    )
    return [
        ("front", front, COL_FRONT, opacity),
        ("right", right, COL_RIGHT, opacity),
        ("top",   top,   COL_TOP,   opacity),
    ]


def main():
    to = datetime.utcnow()
    frm = to - timedelta(days=30)
    data = gql(TOKEN, QUERY, {"user": USERNAME, "from": frm.isoformat() + "Z", "to": to.isoformat() + "Z"})
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
    bar_w = slot * 0.5

    # Isometric projection (top shifts up-right)
    iso_x = 8
    iso_y = -6

    # Soft grid lines
    grid = []
    for i in range(1, 5):
        gy = PAD_T + chart_h - (chart_h / 4 * i)
        grid.append(
            f'<line x1="{PAD_L}" y1="{gy:.1f}" x2="{W - PAD_R}" y2="{gy:.1f}" '
            f'stroke="{COL_GRID}" stroke-width="0.75" stroke-dasharray="3,3"/>'
        )

    base_y = PAD_T + chart_h
    bars = []
    shadows = []

    for i, (date, count) in enumerate(days):
        x = PAD_L + i * slot + (slot - bar_w) / 2
        is_best = (date == best[0] and count > 0)

        if count > 0:
            h = max((count / max_c) * chart_h, 5)
            # Opacity ramp: low days translucent, mid/high opaque.
            # Peak day gets the full opacity and a slightly darker tint.
            ratio = count / max_c
            if is_best:
                opacity = 1.0
            elif ratio >= 0.5:
                opacity = 0.92
            elif ratio >= 0.2:
                opacity = 0.78
            else:
                opacity = 0.62

            # Ground shadow strip (soft, very faint)
            shadows.append(
                f'<path d="M{x:.2f},{base_y+2:.2f} L{x+bar_w:.2f},{base_y+2:.2f} '
                f'L{x+bar_w+iso_x:.2f},{base_y+2+iso_y:.2f} L{x+iso_x:.2f},{base_y+2+iso_y:.2f} Z" '
                f'fill="{COL_SHADOW}" opacity="0.05"/>'
            )

            for face_name, path, color, op in bar_faces(x, base_y, bar_w, h, opacity, iso_x, iso_y):
                # Translucent stroke softens the edge.
                bars.append(
                    f'<path d="{path}" fill="{color}" fill-opacity="{op:.2f}" '
                    f'stroke="{COL_EDGE}" stroke-opacity="0.12" stroke-width="0.6"/>'
                )

            # Value label above the bar (kept only for prominence)
            if count >= max_c * 0.5 or is_best:
                label_y = base_y - h + iso_y - 4
                bars.append(
                    f'<text x="{x + bar_w/2 + iso_x/2:.2f}" y="{label_y:.1f}" '
                    f'text-anchor="middle" fill="{COL_FRONT}" font-size="9.5" '
                    f'font-weight="600" font-family="ui-monospace,monospace">{count}</text>'
                )
        else:
            # Idle day: a soft, very low isometric platform with no fill
            # stroke so it doesn't compete with the real bars.
            shadows.append(
                f'<path d="M{x:.2f},{base_y:.2f} L{x+bar_w:.2f},{base_y:.2f} '
                f'L{x+bar_w+iso_x:.2f},{base_y+iso_y:.2f} L{x+iso_x:.2f},{base_y+iso_y:.2f} Z" '
                f'fill="{COL_GRID}" stroke="{COL_GRID}" stroke-width="0.5"/>'
            )

        # Date labels every 5 days
        if i % 5 == 0:
            label = date[5:]
            bars.append(
                f'<text x="{x + bar_w/2 + iso_x/2:.2f}" y="{base_y + iso_y + 14}" '
                f'text-anchor="middle" fill="#6B7280" font-size="9.5" '
                f'font-family="ui-monospace,monospace">{label}</text>'
            )

    # Baseline
    ground = (
        f'<line x1="{PAD_L}" y1="{base_y:.1f}" x2="{W - PAD_R}" y2="{base_y:.1f}" '
        f'stroke="#D1D5DB" stroke-width="1"/>'
    )

    # Summary pills (slightly softer background than before)
    def pill(x, y, w, label, value):
        return (
            f'<rect x="{x}" y="{y}" width="{w}" height="28" rx="8" '
            f'fill="#FFFFFF" stroke="#D1D5DB" stroke-width="1"/>'
            f'<text x="{x + 12}" y="{y + 18}" fill="#6B7280" font-size="10.5" '
            f'font-family="-apple-system,BlinkMacSystemFont,sans-serif">{esc(label)}</text>'
            f'<text x="{x + w - 12}" y="{y + 18}" text-anchor="end" fill="#1F2937" '
            f'font-size="11.5" font-weight="700" font-family="ui-monospace,monospace">{esc(value)}</text>'
        )

    pill_w = 130
    pill_gap = 14
    pills_y = 22
    p1 = pill(PAD_L, pills_y, pill_w, "Total", str(total))
    p2 = pill(PAD_L + pill_w + pill_gap, pills_y, pill_w, "Daily avg", f"{avg:.1f}")
    p3 = pill(PAD_L + 2 * (pill_w + pill_gap), pills_y, pill_w, "Best day", str(best[1]))
    p4 = pill(PAD_L + 3 * (pill_w + pill_gap), pills_y, pill_w, "Active days", f"{active}/{len(days)}")

    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
        f'<rect width="{W}" height="{H}" fill="#FFFFFF" rx="10"/>',
        f'<text x="{PAD_L}" y="18" fill="#1F2937" font-size="13" font-weight="700" '
        f'font-family="-apple-system,BlinkMacSystemFont,sans-serif">Contributions</text>',
        f'<text x="{W - PAD_R}" y="18" text-anchor="end" fill="#6B7280" font-size="11" '
        f'font-family="-apple-system,sans-serif">{frm.strftime("%b %d")} - {to.strftime("%b %d, %Y")}</text>',
        p1, p2, p3, p4,
        "".join(grid),
        "".join(shadows),
        ground,
        "".join(bars),
        '</svg>',
    ]
    final = chr(10).join(svg_parts)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        f.write(final)
    print(f"generated {OUT}: {total} total, {avg:.1f} avg, best={best[1]}, active={active}/{len(days)}, size={len(final)}")


if __name__ == "__main__":
    main()
