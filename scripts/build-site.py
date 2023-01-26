from github import Github, Repository
from gftools.utils import download_file
from zipfile import ZipFile
from pathlib import Path
import tempfile
import os
import json
from io import BytesIO
from pybars import Compiler, strlist
import humanize
import re
import subprocess

EXCLUDE_LIST = ["Arimo", "Cousine", "Tinos"]

results = json.load(open("docs/noto.json"))
versions = json.load(open("docs/versions.json"))


def _basename(this, item):
    return strlist([os.path.basename(item)])


def _denoto(this, item):
    return strlist([item.replace("Noto ", "")])


def _sizeof(this, item):
    return strlist([humanize.naturalsize(os.path.getsize(item))])


def _gt1(this, options, context):
    if hasattr(context, "__call__"):
        context = context(this)
    if context > 1:
        return options["fn"](this)
    else:
        return options["inverse"](this)


def _ifslim(this, options, context):
    if hasattr(context, "__call__"):
        context = context(this)
    if "slim-variable-ttf" in context:
        return options["fn"](this)
    else:
        return options["inverse"](this)


helpers = {
    "basename": _basename,
    "gt1": _gt1,
    "sizeof": _sizeof,
    "ifslim": _ifslim,
    "denoto": _denoto,
}

def icon_for_platform(platform):
    if "Android" in platform:
        return f'<span class="material-icons" data-toggle="tooltip" title="{platform}"> android </span>'
    if "iOS" in platform:
        return f'<span class="material-icons" data-toggle="tooltip" title="{platform}"> phone_iphone </span>'
    if "macOS" in platform:
        return f'<span class="material-icons" data-toggle="tooltip" title="{platform}"> laptop_mac </span>'
    if "Google Fonts" in platform:
        return f'<img data-toggle="tooltip" title="{platform}" src="gflogo.png" width=18 height=18></img>'
    if "Fedora" in platform:
        return f'<img data-toggle="tooltip" title="{platform}" src="fedora.png" width=18 height=18></img>'
    return platform

compiler = Compiler()
template = open("scripts/template.html", "r").read()
template = compiler.compile(template)

for result in results.values():
    result["has_releases"] = False
    for family_name, family in result.get("families", []).items():
        if family.get("latest_release"):
            result["has_releases"] = True
            latest_version = family["latest_release"]["version"][1:]
            if family_name in versions:
                family["third_party_versions"] = { 
                    k: {
                        "version": versions[family_name][k],
                        "up_to_date": versions[family_name][k] == latest_version,
                        "icon": icon_for_platform(k)
                    }
                    for k in sorted(versions[family_name].keys())
                }
    result["issue_count"] = len(result["issues"])
    result["families_count"] = len(result["families"])

for excluded in EXCLUDE_LIST:
    if excluded in results:
        del results[excluded]

output = template({"results": results}, helpers=helpers)

with open("docs/index.html", "w") as fh:
    fh.write(output)

bug_template = open("scripts/bugreporter.html", "r").read()
bug_template = compiler.compile(bug_template)
output = bug_template({"results": results})
with open("docs/reporter.html", "w") as fh:
    fh.write(output)

json.dump(
    results, open("debug.json", "w"), indent=True, sort_keys=True
)
