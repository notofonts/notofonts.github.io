from github import Github, Repository
from gftools.utils import download_file, fonts_from_zip
from zipfile import ZipFile
from pathlib import Path
import tempfile
import os
import json
from pybars import Compiler
import re
import subprocess


TEESTING = False

print("Fetching existing repos")
g = Github(os.environ["GITHUB_TOKEN"])
org = g.get_organization("notofonts")
org_repos = org.get_repos()
org_names = [r.name for r in org_repos]

subprocess.run(["git", "config", "user.name", "actions-user"])
subprocess.run(["git", "config", "user.email", "actions-user@users.noreply.github.com"])

sources = json.load(open("sources.json"))
if os.path.exists("state.json"):
    state = json.load(open("state.json"))
else:
    state = {}

results = {}

for repo_name in sources.keys():
    if repo_name not in org_names:
        continue

    print(f"Gathering data for {repo_name}")

    repo = g.get_repo("notofonts/" + repo_name)
    results[repo_name] = {
        "title": repo.description,
        "gh_url": "https://notofonts.github.io/" + repo_name,
        "repo_url": "https://www.github.com/notofonts/" + repo_name,
    }

    # Get issues
    results[repo_name]["issues"] = []
    for issue in repo.get_issues():
        results[repo_name]["issues"].append(
            {"title": issue.title, "number": issue.number, "url": issue.html_url}
        )

    if repo_name not in state:
        state[repo_name] = {}

    # Check for new releases
    for release in repo.get_releases():
        m = re.match(r"^(.*)-(v[\d.]+)", release.tag_name)
        if not m:
            print(f"Unparsable release {release.tag_name} in {repo_name}")
            continue
        family, version = m[1], m[2]
        family = re.sub(r"([a-z])([A-Z])", r"\1 \2", family)
        if release.tag_name not in state[repo_name].get("known_releases", []):
            assets = release.get_assets()
            if not assets:
                continue
            latest_asset = assets[0]
            state[repo_name].setdefault("known_releases", []).append(release.tag_name)
            family_thing = (
                state[repo_name].setdefault("families", {}).setdefault(family, {})
            )

            family_thing["latest_release"] = {
                "url": release.html_url,
                "version": version,
                "notes": release.body,
            }

            z = ZipFile(download_file(latest_asset.browser_download_url))
            family_thing["files"] = []
            with tempfile.TemporaryDirectory() as tmpdir:
                fonts = fonts_from_zip(z, tmpdir)
                for font in fonts:
                    newpath = Path("fonts/") / Path(font).relative_to(tmpdir)
                    os.makedirs(newpath.parent, exist_ok=True)
                    family_thing["files"].append(str(newpath))
                    os.rename(font, newpath)
                if not TEESTING:
                    # Add it and tag it
                    subprocess.run(["git", "add", "."])
                    subprocess.run(["git", "commit", "-m", "Add "+release.tag_name])
                    subprocess.run(["git", "tag", release.tag_name])
                    subprocess.run(["git", "push"])
                    subprocess.run(["git", "push", "--tags"])


            # Tweet about the new release or something
    results[repo_name]["families"] = state[repo_name].get("families", {})

# Save state
json.dump(state, open("state.json", "w"), indent=True, sort_keys=True)

for result in results.values():
    for family in result.get("families", {}).values():
        newfiles = {"unhinted": [], "hinted": [], "full": []}
        for file in family.get("files", []):
            if "unhinted" in file:
                newfiles["unhinted"].append(file)
            elif "hinted" in file:
                newfiles["hinted"].append(file)
            elif "full" in file:
                newfiles["full"].append(file)
        family["files"] = newfiles

compiler = Compiler()
template = open("scripts/template.html", "r").read()
template = compiler.compile(template)
output = template({"results": results})

print(json.dumps(results, indent=True))
with open("index.html", "w") as fh:
    fh.write(output)

bug_template = open("scripts/bugreporter.html", "r").read()
bug_template = compiler.compile(bug_template)
output = bug_template({"results": results})
with open("reporter.html", "w") as fh:
    fh.write(output)
