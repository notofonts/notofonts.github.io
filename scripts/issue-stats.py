import requests
import os
from collections import defaultdict, Counter
import json
from pprint import pprint
from datetime import datetime, timedelta

headers = {"Authorization": "bearer " + os.environ["GITHUB_TOKEN"]}
this = datetime.now()

USE_EXISTING = False

releases_per_month = {}

try:
    from tqdm.contrib.concurrent import process_map  # or thread_map
except Exception:
    process_map = map


def run_query(query):
    request = requests.post(
        "https://api.github.com/graphql", json={"query": query}, headers=headers
    )
    if request.status_code == 200:
        return request.json()
    else:
        raise Exception(
            "Query failed to run by returning code of {}. {}".format(
                request.status_code, query
            )
        )


def do_one_repo(reponame):
    issues = []
    pagination = ""
    while True:
        query = """
        query {
          organization(login: "notofonts") {
            repository(name: "%s") {
              issues(first: 100%s) {
                nodes {
                  createdAt
                  closedAt
                  url
                }
                pageInfo {
                  hasNextPage
                  endCursor
                }
              }
            }
          }
        }
    """ % (
            reponame,
            pagination,
        )
        result = run_query(query)
        tier = sources[reponame].get("tier", 3)

        if "data" in result:
            result = result["data"]["organization"]["repository"]["issues"]
        else:
            print(result)
            break
        for issue in result["nodes"]:
            if issue["closedAt"] and issue["closedAt"] <= "2024-01-01":
                continue
            issue["repo"] = reponame
            issue["tier"] = tier
            issues.append(issue)
        if result["pageInfo"]["hasNextPage"]:
            endcursor = result["pageInfo"]["endCursor"]
            pagination = f'after:"{endcursor}"'
        else:
            break
    return issues


def get_releases(rpm):
    pagination = ""
    while True:
        query = """
            query {
              organization(login: "notofonts") {
                repositories(first: 100%s) {
                  nodes {
                    releases(last: 100) {
                      nodes {
                        publishedAt
                        tagName
                        url
                      }
                    }
                  }
                  pageInfo {
                      hasNextPage
                      endCursor
                    }
                }
              }
            }
        """ % (
            pagination
        )
        result = run_query(query)
        if "data" in result:
            result = result["data"]["organization"]["repositories"]
        else:
            print(result)
            return
        for repo in result["nodes"]:
            for release in repo["releases"]["nodes"]:
                if not release["publishedAt"] or release["publishedAt"] <= "2024-01-01":
                    continue
                if "notofonts.github.io" in release["url"]:
                    continue
                published = datetime.fromisoformat(release["publishedAt"].replace("Z",""))
                rpm.setdefault(published.month, []).append(
                    {"tag": release["tagName"], "url": release["url"]}
                )
        if result["pageInfo"]["hasNextPage"]:
            endcursor = result["pageInfo"]["endCursor"]
            pagination = f'after:"{endcursor}"'
        else:
            break

all_results = []
sources = json.load(open("fontrepos.json"))

if __name__ == '__main__':
    get_releases(releases_per_month)
    all_results = process_map(do_one_repo, list(sources.keys()))
    all_results = [item for sublist in all_results for item in sublist]

    json.dump(
        all_results,
        open("all-results.json", "w"),
        indent=True,
        sort_keys=True,
    )


    def last_day_of_month(any_day):
        next_month = any_day.replace(day=28) + timedelta(days=4)
        return next_month - timedelta(days=next_month.day)


    def open_at(date, issues):
        return [x for x in issues if (not x["closedAt"] or x["closedAt"] > str(date)) and x["createdAt"] <= str(date)]


    def opened_during(start, end, issues):
        return [
            x for x in issues if x["createdAt"] >= str(start) and x["createdAt"] <= str(end)
        ]


    def closed_during(start, end, issues):
        return [
            x
            for x in issues
            if x["closedAt"] and x["closedAt"] >= str(start) and x["closedAt"] <= str(end)
        ]


    open_issues = [x for x in all_results if not x["closedAt"]]
    open_per_repo = Counter([x["repo"] for x in open_issues])
    open_per_tier = Counter([x["tier"] for x in open_issues])
    totals_per_month = {}
    closed_per_month = {}
    opened_per_month = {}

    year_to_date = range(1, this.month + 1)

    for i in year_to_date:
        start_of_month = this.replace(month=i, day=1)
        end_of_month = last_day_of_month(start_of_month)
        totals_per_month[i] = len(open_at(start_of_month, all_results))
        closed_per_month[i] = len(closed_during(start_of_month, end_of_month, all_results))
        opened_per_month[i] = len(opened_during(start_of_month, end_of_month, all_results))
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

    from pybars import Compiler
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

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
