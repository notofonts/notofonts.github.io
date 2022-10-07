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

results = json.load(open("docs/noto.json"))

def _basename(this, item):
    return strlist([os.path.basename(item)])
helpers = {"basename": _basename}

compiler = Compiler()
template = open("scripts/template.html", "r").read()
template = compiler.compile(template)
output = template({"results": results}, helpers=helpers)

with open("docs/index.html", "w") as fh:
    fh.write(output)

bug_template = open("scripts/bugreporter.html", "r").read()
bug_template = compiler.compile(bug_template)
output = bug_template({"results": results})
with open("docs/reporter.html", "w") as fh:
    fh.write(output)
