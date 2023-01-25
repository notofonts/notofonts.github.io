# This script gathers Noto versions from third-party sources.
# It's designed to run on Simon's computer, and probably not
# anywhere else.
import json
import os
import platform
import plistlib
import re
from collections import defaultdict
from pathlib import Path

import requests
from fontTools.ttLib import TTFont
from gfpipeline import \
    FontFamilies  # This is a private module, you won't find it
from tqdm import tqdm

MACOS_PATH = Path("/System/Library/Fonts/")
MAC_VERSION = "macOS " + re.sub(r".\d+$", "", platform.mac_ver()[0])

IOS_PATH_1 = Path(
    "/Applications/Xcode.app/Contents/Developer/Platforms/iPhoneOS.platform/Library/Developer/CoreSimulator/Profiles/Runtimes/iOS.simruntime/Contents/Resources/RuntimeRoot/System/Library/Fonts/UnicodeSupport/"
)
IOS_PATH_2 = Path(IOS_PATH_1.parent) / "Core"

ANDROID_PATH = Path("~/Downloads/android_fonts-master/api_level/").expanduser()
LATEST_ANDROID_PATH = sorted(list(ANDROID_PATH.glob("??")))[-1]
IOS_VERSION_PATH = "/Applications/Xcode.app/Contents/Developer/Platforms/iPhoneOS.platform/Library/Developer/CoreSimulator/Profiles/Runtimes/iOS.simruntime/Contents/Info.plist"
IOS_VERSION = plistlib.load(open(IOS_VERSION_PATH, "rb"))["CFBundleExecutable"]

ANDROID_API_VERSION_MAP = {
    "31": "Android 12",
    "32": "Android 12L",
    "33": "Android 13",
}

ANDROID_VERSION = ANDROID_API_VERSION_MAP[LATEST_ANDROID_PATH.stem]

# These will need manual updates
FEDORA_VERSION = "Fedora 38"
FEDORA_SRC = "https://kojipkgs.fedoraproject.org//packages/google-noto-fonts/20201206^1.git0c78c8329/9.fc38/src/google-noto-fonts-20201206^1.git0c78c8329-9.fc38.src.rpm"
FEDORA_TAR = "noto-fonts-0c78c8329.tar.xz"


notoversions = defaultdict(dict)


def tidy_name(name):
    if "Old Italic" not in name:
        name = re.sub(r" Italic", "", name)
    if "Hmong Nyiakeng" in name:
        name = "Noto Serif Nyiakeng Puachue Hmong"
    name = re.sub(r"( (Regular|Bold|Black))+$", "", name)
    name = re.sub(r" PhagsPa$", " Phags Pa", name)
    return name


def tidy_version(name5version):
    version = re.sub(";.*", "", name5version)
    version = re.sub("Version ", "", version)
    return version


def register_version(file, system):
    global notoversions
    ttfont = TTFont(file, fontNumber=0)
    name = tidy_name(ttfont["name"].getDebugName(4))
    if "Emoji" in name:
        return
    version = "%1.3f" % ttfont["head"].fontRevision
    notoversions[name][system] = version


if __name__ == "__main__":
    for file in (IOS_PATH_1).glob("Noto*.tt?"):
        register_version(file, IOS_VERSION)
    for file in (IOS_PATH_2).glob("Noto*.tt?"):
        register_version(file, IOS_VERSION)

    assert "Noto Sans Armenian" in notoversions

    for file in MACOS_PATH.glob("Noto*.tt?"):
        register_version(file, MAC_VERSION)

    for file in (MACOS_PATH / "Supplemental/").glob("Noto*.tt?"):
        register_version(file, MAC_VERSION)

    for file in (LATEST_ANDROID_PATH).glob("Noto*.tt?"):
        register_version(file, ANDROID_VERSION)

    # Fedora 38
    if not os.path.exists(FEDORA_TAR):
        if not os.path.exists("noto-fedora.src.rpm"):
            response = requests.get(FEDORA_SRC, stream=True)
            total_size_in_bytes = int(response.headers.get("content-length", 0))
            print("Downloading Fedora 38 sources")
            progress_bar = tqdm(total=total_size_in_bytes, unit="iB", unit_scale=True)
            with open("noto-fedora.src.rpm", "wb") as file:
                for data in response.iter_content(1024):
                    progress_bar.update(len(data))
                    file.write(data)
            progress_bar.close()
        print("Opening RPM")
        os.system("rpm2cpio noto-fedora.src.rpm | cpio -id noto-fonts-0c78c8329.tar.xz")
    if not os.path.exists("fedora-noto"):
        os.makedirs("fedora-noto")
        os.system(
            " xz -dc " + FEDORA_TAR + " | tar -C fedora-noto -xf - '*Regular.ttf'"
        )

    for file in Path("fedora-noto").glob("**/Noto*.tt?"):
        register_version(file, "Fedora 38")

    # Google Fonts
    versions = FontFamilies(list(notoversions.keys()))
    for family_dict in versions.data:
        notoversions[family_dict["name"]]["Google Fonts"] = tidy_version(
            family_dict["production"]["version_nameid5"]
        )

    json.dump(
        notoversions, open("docs/versions.json", "w"), indent=True, sort_keys=True
    )
