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

compiler = Compiler()
template = open("scripts/template.html", "r").read()
template = compiler.compile(template)

for result in results.values():
    result["has_releases"] = False
    for family in result.get("families", []).values():
        if family.get("latest_release"):
            result["has_releases"] = True
            break
    result["issue_count"] = len(result["issues"])
    result["families_count"] = len(result["families"])

for excluded in EXCLUDE_LIST:
    del results[excluded]

output = template({"results": results}, helpers=helpers)

with open("docs/index.html", "w") as fh:
    fh.write(output)

bug_template = open("scripts/bugreporter.html", "r").read()
bug_template = compiler.compile(bug_template)
output = bug_template({"results": results})
with open("docs/reporter.html", "w") as fh:
    fh.write(output)
