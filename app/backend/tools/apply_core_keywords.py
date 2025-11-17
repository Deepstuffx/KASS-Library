#!/usr/bin/env python3
"""Convert a provided taxonomy into keyword rules and apply them to the
OrganizedLibraryDemo folder. Runs a dry-run by default and can commit changes
with --apply. Produces an undo CSV when applying.

Usage:
  PYTHONPATH=. python app/backend/tools/apply_core_keywords.py --root sandbox/OrganizedLibraryDemo --dry-run
  PYTHONPATH=. python app/backend/tools/apply_core_keywords.py --root sandbox/OrganizedLibraryDemo --apply
"""
from pathlib import Path
import argparse
import csv
import shutil
import os
from typing import Dict, List

from app.backend.tools.refine_sorting import KEYWORD_MAP as EXISTING_KEYWORD_MAP, refine

# User-provided taxonomy (trimmed to keys/arrays provided)
TAXONOMY = {
    "coreCategories": [
        "drums","percussion","bass","synth","keys","guitar","piano","strings",
        "brass","woodwinds","vocals","fx","live sounds","field recording","foley",
        "mallets","bells"
    ],
    "drums": {
        "kicks": ["kick","acoustic kick","electronic kick","808 kick","punchy kick","subby kick","distorted kick","clicky kick"],
        "snares": ["snare","acoustic snare","electronic snare","rimshot","snare rim","snare roll","snare ghost","snare flam","snare fill"],
        "claps": ["clap","stacked clap","wide clap","snap","finger snap"],
        "hats": ["hihat","hi hat","closed hihat","closed hat","open hihat","open hat","hat loop","hi hat loop"],
        "toms": ["tom","floor tom","rack tom"],
        "cymbals": ["ride","ride cymbal","crash","crash cymbal","splash","china cymbal"],
        "breaksAndFills": ["breakbeat","drum break","drum fill","fill","drum loop","drum top loop","top loop"]
    },
    "percussion": {
        "unpitched": ["perc","percussion","percussion loop","percussion one shot","shaker","tambourine","cowbell","woodblock","triangle","blocks","hand drum","frame drum"],
        "handDrums": ["bongo","bongos","conga","djembe","timbale","timbales"],
        "latinEthnic": ["clave","guiro","agogo"]
    },
    "bass": {"core": ["bass","sub bass","bass one shot","bass loop","808","808 one shot","808 kick","reese bass","wobble bass","fm bass","growl bass","sub drop"]},
    "synth": {"core": ["synth","synth melody","synth one shot","synth loop"], "leads": ["lead","lead synth","mono lead","poly lead"], "pads": ["pad","string pad","ambient pad"], "plucks": ["pluck","pluck synth"], "arps": ["arp","arpeggio","arp loop"], "chords": ["synth chord","chords","chord stab"], "textures": ["texture","texture loop","soundscape","drone"]},
    "keys": {"core": ["keys","keys loop","keys melody"], "piano": ["piano","piano loop","piano one shot"], "electric": ["electric piano","electric piano loop","wurlitzer"], "organ": ["organ","organ loop"], "misc": ["chord","chord progression"]},
    "guitar": {"core": ["guitar","guitar loop","guitar riff","guitar chop"], "types": ["electric guitar","acoustic guitar","acoustic guitar loop","clean guitar","overdriven guitar","distorted guitar"], "articulations": ["strum","pluck guitar"]},
    "strings": {"core": ["strings","string riff","string ensemble"], "orchestral": ["violin","viola","cello","double bass","ensemble"]},
    "brassWoodwinds": {"brass": ["brass","trumpet","trombone","horn section"], "woodwinds": ["woodwinds","saxophone","flute","clarinet"]},
    "malletsBells": {"mallets": ["mallets","marimba","vibraphone","xylophone"], "bells": ["bells","music box"]},
    "vocals": {"core": ["vocals","vocal one shot","vocal loop"], "type": ["female vocal","male vocal","choir","background vocals","gang vocals"], "phrases": ["vocal chop","vocal phrase","vocal hook","rap phrase"], "fx": ["vocal fx","vocal adlib","vocal shout","vocal shouts","vocal glitch","vocal riser","vocal stutter"], "processed": ["vocoder","talkbox"], "spoken": ["spoken word","whisper","scream","chant","dialogue"]},
    "fx": {"general": ["fx","sfx","sound fx","transition fx"], "impacts": ["impact","hit fx","cinematic hit","cinematic impact","sub impact","metal hit","wood hit","glass hit","industrial hit","boom"], "motion": ["whoosh","swoosh","sweep","up sweep","down sweep","riser","short riser","long riser","uplifter","downlifter","drop fx","build fx","build up","transition up","transition down"], "reverse": ["reverse","reverse crash","reverse vocal"], "glitch": ["stutter","glitch","glitch hit","glitch loop","bitcrush fx","bit crushed","digital error"], "dj": ["spinback","spin back","rewind fx","tape stop","tape start","scratch","turntable scratch","dj scratch","brake fx"], "spaceAmbience": ["reverb tail","delay throw","echo","ambience","room tone","atmosphere","atmo","impact reverb"], "noiseTexture": ["noise","noise fx","white noise","pink noise","sweep noise","vinyl noise","vinyl crackle","tape noise","tape hiss"], "foleyField": ["foley","foley step","field recording","rain","wind","crowd noise","city ambience","forest ambience","live sounds"]},
    "loopsVsShots": {"loops": ["loop","drum loop","melodic loop","bass loop","synth loop","vocal loop","guitar loop","piano loop","pad loop","arp loop","percussion loop"], "oneShots": ["one shot","oneshot","drum shot","bass one shot","synth one shot","vocal one shot","piano one shot","hit","stab","stabs"]}
}


def flatten_taxonomy(tax: Dict) -> List[tuple]:
    """Return list of (keyword, relative_folder) tuples from taxonomy.
    We try to map sections to our OrganizedLibraryDemo structure.
    """
    rules = []

    # map high-level categories to root folders
    cat_map = {
        'drums': '01 Drums',
        'percussion': '01 Drums/Percussion',
        'bass': '02 Bass',
        'synth': '03 Synths & Leads',
        'keys': '03 Synths & Leads',
        'guitar': '09 Instruments & Real Sounds',
        'piano': '03 Synths & Leads',
        'strings': '09 Instruments & Real Sounds',
        'brass': '09 Instruments & Real Sounds',
        'woodwinds': '09 Instruments & Real Sounds',
        'vocals': '05 Vocals',
        'fx': '04 FX',
        'foley': '04 FX/Foley',
        'mallets': '09 Instruments & Real Sounds/Mallets',
        'bells': '09 Instruments & Real Sounds/Bells',
        'live sounds': '04 FX/Foley',
        'field recording': '04 FX/Foley'
    }

    # handle drums subcategories
    if 'drums' in tax:
        for sub, kws in tax['drums'].items():
            folder = '01 Drums'
            if sub == 'kicks':
                folder = '01 Drums/Kicks'
            elif sub == 'snares':
                folder = '01 Drums/Snares'
            elif sub == 'claps':
                folder = '01 Drums/Claps'
            elif sub == 'hats':
                folder = '01 Drums/Hats'
            elif sub == 'toms':
                folder = '01 Drums/Toms'
            elif sub == 'cymbals':
                folder = '01 Drums/Cymbals'
            elif sub == 'breaksAndFills':
                folder = '01 Drums/Drum Fills'
            for kw in kws:
                rules.append((kw.lower(), folder))

    # percussion
    if 'percussion' in tax:
        for sub, kws in tax['percussion'].items():
            folder = '01 Drums/Percussion'
            for kw in kws:
                rules.append((kw.lower(), folder))

    # bass
    if 'bass' in tax:
        for sub, kws in tax['bass'].items():
            folder = '02 Bass'
            for kw in kws:
                rules.append((kw.lower(), folder))

    # synth
    if 'synth' in tax:
        for sub, kws in tax['synth'].items():
            folder = '03 Synths & Leads'
            if sub == 'pads':
                folder = '03 Synths & Leads/Pads'
            elif sub == 'leads':
                folder = '03 Synths & Leads/Leads'
            elif sub == 'plucks':
                folder = '03 Synths & Leads/Plucks'
            for kw in kws:
                rules.append((kw.lower(), folder))

    # keys
    if 'keys' in tax:
        for sub, kws in tax['keys'].items():
            folder = '03 Synths & Leads'
            if sub == 'piano':
                folder = '03 Synths & Leads/Piano'
            for kw in kws:
                rules.append((kw.lower(), folder))

    # guitar
    if 'guitar' in tax:
        for sub, kws in tax['guitar'].items():
            folder = '09 Instruments & Real Sounds/Guitar'
            for kw in kws:
                rules.append((kw.lower(), folder))

    # strings / brass / woodwinds / mallets
    if 'strings' in tax:
        for sub, kws in tax['strings'].items():
            folder = '09 Instruments & Real Sounds/Strings'
            for kw in kws:
                rules.append((kw.lower(), folder))
    if 'brassWoodwinds' in tax:
        for sub, kws in tax['brassWoodwinds'].items():
            folder = '09 Instruments & Real Sounds/' + ('Brass' if sub == 'brass' else 'Woodwinds')
            for kw in kws:
                rules.append((kw.lower(), folder))
    if 'malletsBells' in tax:
        for sub, kws in tax['malletsBells'].items():
            folder = '09 Instruments & Real Sounds/Mallets' if sub == 'mallets' else '09 Instruments & Real Sounds/Bells'
            for kw in kws:
                rules.append((kw.lower(), folder))

    # vocals
    if 'vocals' in tax:
        for sub, kws in tax['vocals'].items():
            folder = '05 Vocals'
            if sub == 'phrases':
                folder = '05 Vocals/Phrases'
            elif sub == 'fx':
                folder = '05 Vocals/FX'
            for kw in kws:
                rules.append((kw.lower(), folder))

    # fx
    if 'fx' in tax:
        for sub, kws in tax['fx'].items():
            folder = '04 FX'
            if sub == 'impacts':
                folder = '04 FX/Impacts'
            elif sub == 'motion':
                folder = '04 FX/Motion'
            elif sub == 'reverse':
                folder = '04 FX/Reverse'
            elif sub == 'glitch':
                folder = '04 FX/Glitches & Stutters'
            elif sub == 'dj':
                folder = '04 FX/DJ'
            elif sub == 'spaceAmbience':
                folder = '04 FX/Ambience'
            elif sub == 'noiseTexture':
                folder = '04 FX/Noise'
            elif sub == 'foleyField':
                folder = '04 FX/Foley'
            for kw in kws:
                rules.append((kw.lower(), folder))

    # loops vs shots
    if 'loopsVsShots' in tax:
        for sub, kws in tax['loopsVsShots'].items():
            folder = '06 Loops & Grooves' if sub == 'loops' else '07 One Shots'
            for kw in kws:
                rules.append((kw.lower(), folder))

    return rules


def build_keyword_map_from_rules(rules: List[tuple]):
    # convert to list of (keywords_list, relpath) suitable for refine_sorting
    # group by folder
    folder_map = {}
    for kw, folder in rules:
        folder_map.setdefault(folder, []).append(kw)
    keyword_map = []
    for folder, kws in folder_map.items():
        # each map entry: (kw list, rel path)
        keyword_map.append((kws, folder))
    return keyword_map


def run(root: Path, apply: bool = False):
    rules = flatten_taxonomy(TAXONOMY)
    keyword_map = build_keyword_map_from_rules(rules)

    # merge new rules with existing map, preferring new rules first
    merged_map = [(klist, folder) for klist, folder in keyword_map]
    # append existing rules to preserve previous behavior
    for klist, folder in EXISTING_KEYWORD_MAP:
        merged_map.append((klist, folder))

    # write a preview CSV of the merged rules
    preview = Path('sandbox/merged_keyword_rules.csv')
    with preview.open('w', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh)
        w.writerow(['folder', 'keyword'])
        for kws, folder in merged_map:
            for kw in kws:
                w.writerow([folder, kw])
    print('Merged keyword rules written to', preview)

    # perform a dry-run refine using the merged_map by monkey-patching refine_sorting.KEYWORD_MAP
    import importlib
    import app.backend.tools.refine_sorting as rs_mod

    # backup existing
    old_map = rs_mod.KEYWORD_MAP
    try:
        rs_mod.KEYWORD_MAP = []
        # convert merged_map to same shape as KEYWORD_MAP: list of (keywords_list, rel)
        for kws, folder in merged_map:
            rs_mod.KEYWORD_MAP.append((kws, folder))

        # run refine in dry-run mode
        print('Running refine (dry-run) with merged rules...')
        rs_mod.refine(Path(root), dry_run=True)

        if apply:
            # when applying, run refine to actually move files and produce undo log
            print('Applying moves now...')
            # collect moves by invoking refine with move, but we need an undo log
            undo_log = Path('sandbox/undo_moves.csv')
            moved_entries = []
            # naive approach: walk and move matching files according to new KEYWORD_MAP
            for dirpath, dirnames, filenames in os.walk(root):
                for fn in filenames:
                    src = Path(dirpath) / fn
                    # find matching target
                    target = None
                    for kws, folder in rs_mod.KEYWORD_MAP:
                        for kw in kws:
                            if kw in fn.lower():
                                target = Path(folder) / fn
                                break
                        if target:
                            break
                    if target:
                        dest_dir = Path(root) / target.parent
                        dest_dir.mkdir(parents=True, exist_ok=True)
                        dest = dest_dir / fn
                        if src.resolve() == dest.resolve():
                            continue
                        shutil.move(str(src), str(dest))
                        moved_entries.append((str(src), str(dest)))

            # write undo log
            with undo_log.open('w', newline='', encoding='utf-8') as fh:
                w = csv.writer(fh)
                w.writerow(['src', 'dest'])
                for s, d in moved_entries:
                    w.writerow([s, d])
            print('Applied moves and wrote undo log to', undo_log)

    finally:
        rs_mod.KEYWORD_MAP = old_map


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--root', default='sandbox/OrganizedLibraryDemo')
    p.add_argument('--apply', action='store_true')
    args = p.parse_args()
    run(Path(args.root), apply=args.apply)


if __name__ == '__main__':
    main()
