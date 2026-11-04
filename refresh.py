#!/usr/bin/env python3
"""Refresh Lunch Roulette's restaurant list from the DoorDash CLI.

Runs read-only `dd-cli search` calls from the office, merges the results,
and rewrites the PLACES block in lunch-roulette.html. Never touches carts
or orders. Sign in first with `dd-cli login`.

    python3 refresh.py            # search, then update lunch-roulette.html
    python3 refresh.py --dry-run  # search and print, change nothing
"""
import datetime
import json
import os
import re
import shutil
import string
import subprocess
import sys
import time

# The office location lives in office.json (not committed): {"lat": 35.0, "lng": -79.0}
HERE = os.path.dirname(os.path.abspath(__file__))
try:
    with open(os.path.join(HERE, "office.json")) as f:
        _office = json.load(f)
    OFFICE = (_office["lat"], _office["lng"])
except (OSError, KeyError, ValueError):
    sys.exit('Create office.json next to refresh.py with the office location: {"lat": 35.0, "lng": -79.0}')
MAX_MI = 5.0
HTML = os.path.join(HERE, "lunch-roulette.html")
INTENT = "Building a random lunch picker for a small office so the group can choose a restaurant"

# Search text -> cuisine label. A place found by several searches gets the
# label of the one where it ranked highest; "lunch" catches everything else.
SEARCHES = [
    ("mexican", "Mexican"), ("tacos", "Mexican"),
    ("thai", "Thai"), ("vietnamese pho", "Vietnamese"),
    ("chinese", "Chinese"), ("korean", "Korean"),
    ("sushi", "Japanese"), ("ramen", "Japanese"),
    ("indian", "Indian"), ("nepalese momo", "Himalayan"),
    ("mediterranean", "Mediterranean"), ("greek", "Mediterranean"),
    ("italian", "Pizza & Italian"), ("pizza", "Pizza & Italian"),
    ("burgers", "Burgers & dogs"), ("hot dogs", "Burgers & dogs"),
    ("sandwiches", "Sandwiches"), ("deli", "Sandwiches"),
    ("salad bowls", "Bowls & salads"), ("poke", "Bowls & salads"),
    ("bbq", "Barbecue"), ("southern", "Southern"),
    ("wings", "Wings"), ("fried chicken", "Chicken"),
    ("latin peruvian", "Latin American"), ("caribbean", "Caribbean"),
    ("lunch", "American"),
]
# A word in the name beats the search ranking.
NAME_CUISINE = [
    (r"taco|cantina|mexican|taqueria|burrito", "Mexican"),
    (r"pizza|pizzeria|italian|ristorante", "Pizza & Italian"),
    (r"sushi|hibachi|japanese|ramen|tokyo", "Japanese"),
    (r"\bthai\b|siam|bangkok", "Thai"),
    (r"\bpho\b|banh mi|vietnam", "Vietnamese"),
    (r"indian|tandoori|curry|masala", "Indian"),
    (r"himalayan|momo|nepal", "Himalayan"),
    (r"korean|bonchon|\bkpot\b", "Korean"),
    (r"chinese|\bwok\b|szechuan|hunan|hunam|dumpling", "Chinese"),
    (r"mediterranean|greek|gyro|yeero|falafel|cava\b", "Mediterranean"),
    (r"poke|bowls?\b|salad", "Bowls & salads"),
    (r"burger|\bdogs?\b", "Burgers & dogs"),
    (r"wings?\b|buffalo", "Wings"),
    (r"chicken", "Chicken"),
    (r"\bdeli\b|sandwich|subs?\b", "Sandwiches"),
    (r"bbq|barbecue|smokehouse", "Barbecue"),
    (r"steakhouse", "Steakhouse"),
    (r"peru|empanada|latin", "Latin American"),
    (r"jamaica|caribbean", "Caribbean"),
]

# Chains that count as fast food. Matched against the name with punctuation removed.
FAST_FOOD = [
    "mcdonalds", "subway", "chickfila", "freddys", "charleys", "raising canes",
    "chipotle", "wendys", "burger king", "taco bell", "bojangles", "popeyes",
    "kfc", "arbys", "sonic drivein", "jersey mikes", "jimmy johns", "firehouse subs",
    "five guys", "zaxbys", "cook out", "hardees", "dairy queen", "dominos",
    "papa johns", "pizza hut", "little caesars", "wingstop", "panda express",
    "moes southwest", "qdoba", "dunkin", "starbucks", "krispy kreme", "shake shack",
    "jack in the box", "whataburger", "culvers", "steak n shake", "checkers",
    "churchs", "cookout", "potbelly", "mod pizza", "smoothie king",
    "tropical smoothie", "salad and go", "taco johns", "del taco", "white castle",
]
# Places that aren't lunch: dessert, coffee, drinks.
NOT_LUNCH = re.compile(r"\b(ice cream|gelato|frozen yogurt|yogurt|donut|doughnut|bakery|cupcake|"
                       r"bubble tea|boba|milk ?tea|coffee|smoothie|juice|cookies?|creamery|dessert)\b", re.I)


def dd_cli():
    return shutil.which("dd-cli") or os.path.expanduser("~/.local/bin/dd-cli")


def search(query):
    cmd = [dd_cli(), "--json-output", "search", "-q", query,
           "--lat", str(OFFICE[0]), "--lng", str(OFFICE[1]),
           "--limit", "50", "--intent", INTENT]
    out = subprocess.run(cmd, capture_output=True, text=True)
    if out.returncode:
        sys.exit(f"dd-cli search {query!r} failed:\n{out.stderr or out.stdout}")
    return json.loads(out.stdout).get("stores", [])


def squash(name):
    return re.sub(r"[^a-z0-9 ]", "", name.lower().replace("-", ""))


def is_fast(name):
    s = squash(name)
    return any(re.search(rf"\b{re.escape(chain)}\b", s) for chain in FAST_FOOD)


def tidy(name):
    # Drop trailing branch addresses and stray dashes: "Amante Gourmet Pizza - 300 East Main Street".
    name = re.sub(r"\s+-\s+\d.*$|\s*-$", "", name.strip())
    return string.capwords(name) if name.isupper() else name


def cuisine_for(name, ranks):
    for pattern, label in NAME_CUISINE:
        if re.search(pattern, name, re.I):
            return label
    # ranks: {cuisine label: best position in that search}; "American" is the lunch catch-all.
    best = min(ranks.items(), key=lambda kv: (kv[1], kv[0] == "American"))
    return best[0]


def reviews(n):
    if not n:
        return ""
    if n >= 1000:
        return f"{n // 1000}k+"
    if n >= 100:
        return f"{n // 100 * 100}+"
    return f"{n // 10 * 10}+" if n >= 10 else str(n)


def main():
    dry = "--dry-run" in sys.argv
    found, ranks, dropped = {}, {}, set()
    for query, cuisine in SEARCHES:
        stores = search(query)
        print(f"{query:>16}: {len(stores)} places", file=sys.stderr)
        for rank, s in enumerate(stores):
            sid = int(s["store_id"])
            name = tidy(s.get("verified_name") or s["name"])
            mi = round((s.get("distance_meters") or 0) / 1609.34, 1)
            if mi > MAX_MI:
                continue
            if NOT_LUNCH.search(name):
                dropped.add(f"{name} (not lunch)")
                continue
            # Next opening after 1 PM means dinner only (judged by the next open day's hours).
            opens = s.get("next_open_time_asap_pickup_ms")
            if opens and datetime.datetime.fromtimestamp(opens / 1000).hour >= 13:
                dropped.add(f"{name} (opens {datetime.datetime.fromtimestamp(opens / 1000):%-I:%M %p})")
                continue
            found.setdefault(sid, (name, s, mi))
            r = ranks.setdefault(sid, {})
            r[cuisine] = min(r.get(cuisine, rank), rank)
        time.sleep(0.5)

    rows = sorted(([sid, name, cuisine_for(name, ranks[sid]), s.get("rating"), reviews(s.get("review_count")),
                    mi, is_fast(name)] for sid, (name, s, mi) in found.items()), key=lambda r: r[5])
    fast = [r[1] for r in rows if r[6]]
    print(f"\n{len(rows)} places within {MAX_MI} mi; fast food: {', '.join(fast) or 'none'}", file=sys.stderr)
    if dropped:
        print("Dropped: " + ", ".join(dropped), file=sys.stderr)
    if dry:
        for r in rows:
            print(r)
        return

    today = datetime.date.today()
    width = max(len(json.dumps(r[1])) for r in rows) + 1
    lines = [f"  // DoorDash CLI searches from the office, {today:%b %-d, %Y}. Run refresh.py to update.",
             "  // [store, name, cuisine, rating, reviews, mi, fast]"]
    for sid, name, cuisine, rating, rev, mi, is_ff in rows:
        cells = [f"{sid},".ljust(10), (json.dumps(name) + ",").ljust(width), (json.dumps(cuisine) + ",").ljust(17),
                 f"{rating if rating is not None else 'null'},", json.dumps(rev) + ",", str(mi)]
        lines.append("  [" + " ".join(cells) + (", true" if is_ff else "") + "],")
    block = "\n".join(lines)

    html = open(HTML).read()
    html, n = re.subn(r"(// BEGIN PLACES\n).*?(\n\s*// END PLACES)", lambda m: m[1] + block + m[2], html, flags=re.S)
    if n != 1:
        sys.exit("Couldn't find the // BEGIN PLACES ... // END PLACES block in lunch-roulette.html")
    note = (f"{len(rows)} places from DoorDash within {MAX_MI:g} mi of the office, sorted by distance. "
            f"Ratings as of {today:%b %-d, %Y}. Uncheck any place the boss won’t eat.")
    html = re.sub(r"<footer>.*?</footer>", f"<footer>{note}</footer>", html, flags=re.S)
    open(HTML, "w").write(html)
    print(f"Updated {HTML}", file=sys.stderr)


if __name__ == "__main__":
    main()
