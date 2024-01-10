import json
import os
from fontTools.ttLib import TTFont
from fontTools.merge import Merger, Options

tiers = json.load(open('../fontrepos.json'))
state = json.load(open('../state.json'))
warnings = []

def megamerge(final_target, base_font, tier_predicate, banned, modulation):
    glyph_count = len(TTFont(base_font).getGlyphOrder())
    selected_repos = [k for k, v in tiers.items() if tier_predicate(v.get("tier", 4))]
    selected_repos = [k for k in selected_repos if k not in banned]
    selected_repos = sorted(selected_repos, key=lambda k: tiers[k]["tier"])
    mergelist = [base_font]
    for repo in selected_repos:
        if "families" not in state[repo]:
            print(f"Skipping odd repo {repo} (no families)")
            continue
        selected_families = [x for x in state[repo]["families"].keys() if modulation in x and "UI" not in x]
        if not selected_families:
            continue
        files = state[repo]["families"][selected_families[0]]["files"]
        files = [ x for x in files if "Regular.ttf" in x and "UI" not in x]
        target = None
        for file in files:
            if "/hinted/" in file:
                target = file
                break
        if target is None:
            for file in files:
                if "/unhinted/" in file:
                    target = file
                    break
        if target is None:
            print(f"Couldn't find a target for {repo}")
            continue
        target_font = TTFont("../"+target)
        glyph_count += len(target_font.getGlyphOrder())
        if glyph_count > 65535:
            warnings.append(f"Too many glyphs while building {final_target}, stopped at {repo}")
            break
        mergelist.append("../"+target)
    print("Merging: ")
    for x in mergelist:
        print("  "+os.path.basename(x))
    merger = Merger(options=Options(drop_tables=["vmtx", "vhea", "MATH"]))
    merged = merger.merge(mergelist)
    merged.save(final_target)


for modulation in ["Sans", "Serif"]:
    banned = ["duployan", "latin-greek-cyrillic", "sign-writing", "test"]
    if modulation == "sans":
        banned.append("devanagari")  # Already included
    megamerge(f"Noto{modulation}Living-Regular.ttf", 
            base_font=f"../fonts/Noto{modulation}/googlefonts/ttf/Noto{modulation}-Regular.ttf",
            tier_predicate= lambda x: x <= 3,
            banned=banned,
            modulation=modulation,
            )
    megamerge(f"Noto{modulation}Historical-Regular.ttf", 
            base_font=f"../fonts/Noto{modulation}/googlefonts/ttf/Noto{modulation}-Regular.ttf",
            tier_predicate= lambda x: x > 3,
            banned=banned,
            modulation=modulation
            )

if warnings:
    print("\n\nWARNINGS:")
    for w in warnings:
        print(w)
else:
    print("Completed successfully")