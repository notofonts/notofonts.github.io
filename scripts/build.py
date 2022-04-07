from dataclasses import replace
from github import Github, Repository
from gftools.utils import download_file, fonts_from_zip
from zipfile import ZipFile
from pathlib import Path
import tempfile
import os
import json
from pybars import Compiler
import re


print("Fetching existing repos")
g = Github(os.environ["GITHUB_TOKEN"])
org = g.get_organization("notofonts")
org_repos = org.get_repos()
org_names = [r.name for r in org_repos]

sources = json.load(open("sources.json"))

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

    # Check for new releases
    for release in repo.get_releases():
        m = re.match(r"^(.*)-(v[\d.]+)", release.tag_name)
        if not m:
            print(f"Unparsable release {release.tag_name} in {repo_name}")
            continue
        family, version = m[1], m[2]
        family = re.sub(r"([a-z])([A-Z])", r"\1 \2", family)
        if release.tag_name not in sources[repo_name].get("known_releases", []):
            assets = release.get_assets()
            if not assets:
                continue
            latest_asset = assets[0]
            sources[repo_name].setdefault("known_releases", []).append(release.tag_name)
            family_thing = (
                sources[repo_name].setdefault("families", {}).setdefault(family, {})
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
                    parts = Path(font).relative_to(tmpdir).parts[1:]
                    newpath = Path(os.path.join(*parts))
                    os.makedirs(newpath.parent, exist_ok=True)
                    family_thing["files"].append(str(newpath))
                    os.rename(font, newpath)

            # Tweet about the new release or something
    results[repo_name]["families"] = sources[repo_name].get("families", {})

compiler = Compiler()
template = open("scripts/template.html", "r").read()
template = compiler.compile(template)
output = template({"results": results})

# Save sources
json.dump(sources, open("sources-new.json", "w"), indent=True, sort_keys=True)

print(json.dumps(results, indent=True))
with open("index.html", "w") as fh:
    fh.write(output)
