from github import Github, Repository
from gftools.utils import download_file
from zipfile import ZipFile
from pathlib import Path
import tempfile
import os
import json
from io import BytesIO
from pybars import Compiler, strlist
import re
import subprocess


TESTING = False
SPECIAL_REPOS = [
    "notofonts.github.io",
    "overview",
    ".github",
    ".allstar",
    "notobuilder",
    "noto-data-dev",
    "noto-docs",
    "noto-project-template",
    "notoglot-mini",
]


def fonts_from_zip(zipfile, dst=None):
    """Unzip fonts. If not dst is given unzip as BytesIO objects"""
    fonts = []
    for filename in zipfile.namelist():
        if filename.endswith(".ttf") or filename.endswith(".otf"):
            if dst:
                target = os.path.join(dst, filename)
                zipfile.extract(filename, dst)
                fonts.append(target)
            else:
                fonts.append(BytesIO(zipfile.read(filename)))
    return fonts


def tree_has_new_files():
    ls = subprocess.run(["git", "ls-files", "--others"], capture_output=True)
    return ls.stdout


print("Fetching existing repos")
g = Github(os.environ["GITHUB_TOKEN"])
org = g.get_organization("notofonts")
org_repos = org.get_repos()
org_names = [r.name for r in org_repos]

subprocess.run(["git", "config", "user.name", "actions-user"])
subprocess.run(["git", "config", "user.email", "actions-user@users.noreply.github.com"])

to_push = []

fontrepos = json.load(open("fontrepos.json"))
if os.path.exists("state.json"):
    state = json.load(open("state.json"))
else:
    state = {}

results = {}

for repo_name in org_names:
    if repo_name in SPECIAL_REPOS:
        continue
    repo = g.get_repo("notofonts/" + repo_name)
    if repo.archived:
        continue
    if repo_name not in fontrepos:
        print("Unknown repo %s; is it missing from fontrepos?" % repo_name)
        continue

    print(f"Gathering data for {repo_name}")

    repo = g.get_repo("notofonts/" + repo_name)
    results[repo_name] = {
        "title": repo.description,
        "tier": fontrepos[repo_name].get("tier", 3),
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
    releases = repo.get_releases()
    for release in sorted(
        releases, key=lambda r: r.published_at.isoformat() if r.published_at else ""
    ):
        m = re.match(r"^(.*)-(v[\d.]+)", release.tag_name)
        if not m:
            print(f"Unparsable release {release.tag_name} in {repo_name}")
            continue
        if release.draft:
            continue
        family, version = m[1], m[2]
        family = re.sub(r"([a-z])([A-Z])", r"\1 \2", family)
        if release.tag_name in state[repo_name].get("known_releases", []):
            continue
        assets = release.get_assets()
        if not assets:
            continue
        latest_asset = assets[0]
        state[repo_name].setdefault("known_releases", []).append(release.tag_name)
        family_thing = (
            state[repo_name].setdefault("families", {}).setdefault(family, {})
        )

        body = release.body
        if not body:
            tag_sha = repo.get_git_ref("tags/" + release.tag_name).object.sha
            try:
                body = repo.get_git_tag(tag_sha).message
            except Exception as e:
                print("Couldn't retrieve release message for %s" % release.tag_name)

        family_thing["latest_release"] = {
            "url": release.html_url,
            "version": version,
            "notes": body,
        }

        if release.published_at:
            family_thing["latest_release"][
                "published"
            ] = release.published_at.isoformat()

        try:
            z = ZipFile(download_file(latest_asset.browser_download_url))
            family_thing["files"] = []
            with tempfile.TemporaryDirectory() as tmpdir:
                fonts = fonts_from_zip(z, tmpdir)
                for font in fonts:
                    newpath = Path("fonts/") / Path(font).relative_to(tmpdir)
                    os.makedirs(newpath.parent, exist_ok=True)
                    family_thing["files"].append(str(newpath))
                    os.rename(font, newpath)
                if tree_has_new_files() and not TESTING:
                    # Add it and tag it
                    subprocess.run(["git", "add", "."])
                    subprocess.run(["git", "commit", "-m", "Add " + release.tag_name])
                    subprocess.run(["git", "tag", release.tag_name])
                    to_push.append(release.tag_name)
        except Exception as e:
            print("Couldn't fetch download for %s" % latest_asset.browser_download_url)

            # Tweet about the new release or something
    results[repo_name]["families"] = state[repo_name].get("families", {})

subprocess.run(["git", "push"])
for tag in to_push:
    subprocess.run(["git", "push", "origin", tag])

# Save state
json.dump(state, open("state.json", "w"), indent=True, sort_keys=True)

for result in results.values():
    for family in result.get("families", {}).values():
        newfiles = {"unhinted": [], "hinted": [], "full": []}
        for file in sorted(family.get("files", [])):
            if "unhinted" in file:
                newfiles["unhinted"].append(file)
            elif "hinted" in file:
                newfiles["hinted"].append(file)
            elif "full" in file:
                newfiles["full"].append(file)
        family["files"] = newfiles

json.dump(results, open("docs/noto.json", "w"), indent=True, sort_keys=True)
