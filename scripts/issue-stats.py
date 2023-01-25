from github import Github, Repository
import os
import json
from datetime import datetime
from collections import Counter
from pybars import Compiler
import matplotlib

try:
    import tqdm

    progress = tqdm.tqdm
except Exception:
    progress = lambda x: x

matplotlib.use("Agg")
import matplotlib.pyplot as plt


g = Github(os.environ["GITHUB_TOKEN"])
sources = json.load(open("fontrepos.json"))

this = datetime.now()

closed_per_month = Counter()
opened_per_month = Counter()
open_per_repo = Counter()
open_per_tier = Counter()
releases_per_month = {}
totals_per_month = {}
issues_by_age = {}

total = 0
for repo_name in progress(list(sources.keys())):
    # if repo_name not in org_names:
    # continue
    repo = g.get_repo("notofonts/" + repo_name)
    issues = repo.get_issues(state="all")
    tier = sources[repo_name].get("tier", 3)
    for i in issues:
        if i.state == "open":
            total += 1
            open_per_repo[repo_name] += 1
            open_per_tier[tier] += 1
            if i.created_at.year == this.year:
                opened_per_month[i.created_at.month] += 1
        elif i.closed_at.year == this.year:
            closed_per_month[i.closed_at.month] += 1

    releases = repo.get_releases()
    for release in sorted(
        releases, key=lambda r: r.published_at.isoformat() if r.published_at else ""
    ):
        if release.draft:
            continue
        releases_per_month.setdefault(release.published_at.month, []).append(
            {"tag": release.tag_name, "url": release.html_url}
        )

# Back-compute totals per month
totals_per_month[this.month] = total
for m in range(this.month, 0, -1):
    total += closed_per_month[m] - opened_per_month[m]
    totals_per_month[m] = total

# Save it
json.dump(
    {
        "opened_per_month": opened_per_month,
        "closed_per_month": closed_per_month,
        "totals_per_month": totals_per_month,
        "open_per_repo": open_per_repo,
        "open_per_tier": open_per_tier,
        "releases_per_month": releases_per_month,
    },
    open("docs/issues.json", "w"),
    indent=True,
    sort_keys=True,
)

year_to_date = range(1, this.month + 1)

months = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
][: this.month]
totals = [totals_per_month[i] for i in year_to_date]

fig, ax1 = plt.subplots()
ax2 = ax1.twinx()

bars = ax1.bar(
    months,
    [totals_per_month[i] for i in year_to_date],
    label="Total",
    color="#aaaaffaa",
)
ax1.bar_label(bars)
ax1.axes.get_yaxis().set_visible(False)

lns1 = ax2.plot(
    months,
    [opened_per_month[i] for i in year_to_date],
    marker=".",
    label="Opened",
    color="red",
    linewidth=3,
)
lns2 = ax2.plot(
    months,
    [closed_per_month[i] for i in year_to_date],
    marker="+",
    label="Closed",
    color="green",
    linewidth=3,
)

lines, labels = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax2.legend(lines + lines2, labels + labels2, loc="lower left")
plt.title("Issues opened, closed, and open")
plt.savefig("docs/open-closed.png")


## Top 10 scripts
top_10 = sorted(open_per_repo.most_common(10), key=lambda x: -x[1])
labels, values = list(zip(*top_10))
fig, ax = plt.subplots()
bars = ax.bar(labels, values)
ax.bar_label(bars)
plt.title("Repositories with most open issues")
plt.xticks(rotation=60)
plt.tight_layout()
plt.savefig("docs/top-10.png")


# Low hanging fruit and tiers
low_hanging = {}
tiers = {1: [], 2: [], 3: [], 4: [], 5: []}
for k, v in open_per_repo.items():
    if v == 0:
        continue
    tier = sources[k].get("tier", 3)
    tiers[tier].append({"repo": k, "issues": v})
    if v > 10:
        continue
    low_hanging.setdefault(v, []).append(k)
low_hanging = [
    {"issues": k, "repos": low_hanging[k]} for k in sorted(low_hanging.keys())
]

tiers = {k: sorted(v, key=lambda i: -i["issues"]) for k, v in tiers.items()}

labels = [1, 2, 3, 4, 5]
values = [open_per_tier.get(l, 0) for l in labels]
fig, ax = plt.subplots()
bars = ax.bar(labels, values)
ax.bar_label(bars)
plt.title("Open issues per tier")
plt.tight_layout()
plt.savefig("docs/per-tier.png")

## Releases per month
release_count_per_month = [len(releases_per_month.get(i, [])) for i in year_to_date]
fig, ax = plt.subplots()
bars = ax.bar(months, release_count_per_month)
ax.bar_label(bars)
plt.title("Releases per month")
plt.savefig("docs/releases.png")

monthly_stats = [
    {
        "month": months[i - 1],
        "opened": opened_per_month.get(i, 0),
        "closed": closed_per_month.get(i, 0),
        "releases": releases_per_month.get(i, []),
        "releases_count": len(releases_per_month.get(i, [])),
    }
    for i in year_to_date
]

compiler = Compiler()
template = open("scripts/analytics-template.html", "r").read()
template = compiler.compile(template)
output = template(
    {
        "monthly_stats": monthly_stats,
        "top_10": [{"repo": k, "count": v} for k, v in top_10],
        "low_hanging": low_hanging,
        "tiers": tiers,
    }
)

with open("docs/analytics.html", "w") as fh:
    fh.write(output)
