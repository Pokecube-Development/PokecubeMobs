import json
from ignore_list import isIgnored
from legacy_renamer import find_old_name, to_model_form, find_new_name, entry_name, banned_form,\
                  is_extra_form, TAG_IGNORE, MEGA_BASE_MAP
import utils
from utils import get_form, get_pokemon, get_species, default_or_latest, get_pokemon_index, url_to_id, dump_file, DATA_DIR, TAG_DATA_DIR, ASSET_DIR
from moves_converter import convert_old_move_name
from model_processor import process_model
import os
from glob import glob
import shutil
from types import SimpleNamespace

LOCATION_AREA = "location-area"

def convert_spawns():

    opts = utils.get_valid_numbers(LOCATION_AREA)
    n = 0
    for key, i in opts.items():
        # if i < 30:
        #     continue
        if "route" in key:
            data = utils.get(LOCATION_AREA, i)
            print(key, i)
            rates = data.encounter_method_rates
            location = data.location.name
            spawns = data.pokemon_encounters
            rate_map = {}
            for rate in rates:
                name = rate.encounter_method.name
                total = 0
                num = len(rate.version_details)
                for det in rate.version_details:
                    total += det.rate
                total /= num
                rate_map[name] = total*0.01
            spawn_map = {}
            for spawn in spawns:
                entry = spawn.pokemon.name
                listing = spawn.version_details
                entryOpts = {}
                entry_cache = []
                for det in listing:
                    sub_dets = det.encounter_details
                    for sub_det in sub_dets:
                        method = sub_det.method.name
                        if method == "gift":
                            continue
                        lvls = [sub_det.min_level, sub_det.max_level]
                        conditions = sub_det.condition_values
                        chance = sub_det.chance * 0.01
                        spawn_entry = {
                            "method": method,
                            "lvls": lvls,
                            "chance": chance,
                        }
                        if conditions != None and len(conditions)>0:
                            conditions = [c.name for c in conditions if not "slot2-" in c.name]
                            if len(conditions) > 0:
                                spawn_entry["conditions"] = conditions
                        cache_val = f"{spawn_entry}"
                        if not cache_val in entry_cache:
                            del spawn_entry["method"]
                            if not method in entryOpts:
                                entryOpts[method] = []
                            entryOpts[method].append(spawn_entry)
                            entry_cache.append(cache_val)
                if len(entryOpts) > 0:
                    spawn_map[entry] = entryOpts

            print(location)
            print(rate_map)
            for entry, entryOpts in spawn_map.items():
                print(entry)
                for key, e in entryOpts.items():
                    print(f" {key}:")
                    for ee in e:
                        print(f"   {ee}")
            n += 1
            if(n > 3):
                break


if __name__ == "__main__":
    convert_spawns()