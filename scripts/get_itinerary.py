"""Fetch a structured itinerary from the API and print it as tables.

Usage:
    python scripts/get_itinerary.py resp_xxx
    python scripts/get_itinerary.py resp_xxx --url http://127.0.0.1:8000
    python scripts/get_itinerary.py resp_xxx --json     # raw JSON instead of tables
"""
import argparse
import json
import sys
import urllib.error
import urllib.request

DEFAULT_URL = "https://ai-travel-advisor-ot90.onrender.com"


def fetch(base_url: str, response_id: str) -> dict:
    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/itinerary",
        data=json.dumps({"previous_response_id": response_id}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        return json.load(resp)


def table(headers: list, rows: list) -> str:
    rows = [[str(c).replace("\n", " ").replace("|", "/") for c in r] for r in rows]
    widths = [max(len(h), *(len(r[i]) for r in rows)) for i, h in enumerate(headers)]
    line = lambda cells: "| " + " | ".join(c.ljust(w) for c, w in zip(cells, widths)) + " |"
    sep = "|-" + "-|-".join("-" * w for w in widths) + "-|"
    return "\n".join([line(headers), sep, *(line(r) for r in rows)])


def render(data: dict) -> str:
    if not data["ready"]:
        return f"Not ready yet. The advisor needs: {data['clarification']}"
    it = data["itinerary"]
    cur = it["budget"]["currency"]
    out = [
        f"# {it['title']}",
        f"{it['destination']} - {it['duration_days']} days\n",
        it["summary"],
        "",
    ]
    for day in it["days"]:
        out.append(f"## Day {day['day']}: {day['theme']}")
        out.append(table(
            ["When", "Activity", "Details", f"Cost ({cur})"],
            [[a["time_of_day"], a["title"], a["description"], f"{a['estimated_cost']:.2f}"]
             for a in day["activities"]],
        ))
        out.append("")
    out.append("## Practical tips")
    out.extend(f"- {t}" for t in it["tips"])
    out.append("\n## Estimated budget")
    out.append(table(
        ["Category", f"Amount ({cur})"],
        [[i["category"], f"{i['amount']:.2f}"] for i in it["budget"]["items"]]
        + [["TOTAL", f"{it['budget']['total']:.2f}"]],
    ))
    u = data["conversation_usage"]
    out.append(f"\n[tokens in/out: {u['input_tokens']}/{u['output_tokens']} | est. cost: ${u['cost_usd']:.4f}]")
    return "\n".join(out)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("response_id", help="response_id returned by the last /chat call")
    p.add_argument("--url", default=DEFAULT_URL, help=f"API base URL (default: {DEFAULT_URL})")
    p.add_argument("--json", action="store_true", help="print raw JSON")
    args = p.parse_args()
    try:
        data = fetch(args.url, args.response_id.strip().strip('"'))
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code}: {e.read().decode()[:300]}", file=sys.stderr)
        return 1
    except urllib.error.URLError as e:
        print(f"Cannot reach {args.url}: {e.reason}", file=sys.stderr)
        return 1
    print(json.dumps(data, indent=2, ensure_ascii=False) if args.json else render(data))
    return 0


if __name__ == "__main__":
    sys.exit(main())
