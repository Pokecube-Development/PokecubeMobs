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

# Uncomment these to generate all of the files in the correct spots
#
# If just updating pokedex entries, leave these commented out, and instead use pokedex_updater.py after running this script.
#
#

entry_generate_dir = f'{DATA_DIR}/database/pokemobs/pokedex_entries/'
mega_rule_dir = f'{DATA_DIR}/database/pokemobs/mega_evos/'
evos_rule_dir = f'{DATA_DIR}/database/pokemobs/evolutions/'
materials_generate_dir = f'{DATA_DIR}/database/pokemobs/materials/'
ability_lang_generate_dir = f'{ASSET_DIR}/pokecube_abilities/lang/'
mob_lang_generate_dir = f'{ASSET_DIR}/pokecube_mobs/lang/'

UPDATE_EXAMPLE = True
WARN_NO_EXP = True
WARN_NO_OLD_ENTRY = False

MEGA_SUFFIX = [
    '-mega',
    '-mega-x',
    '-mega-y',
    '-mega-z',
    '-primal',
    '-battle-bond',
    '-ash',
]
GMAX_SUFFIX = [
    '-gmax',
    '-eternamax',
]

NO_SHINY = [
    'vivillon'
]

base_exp_fixes = json.load(open('./data/pokemobs/fix_base_exp.json', 'r'))
evo_moves = json.load(open('./data/pokemobs/evo_moves.json', 'r'))

def no_shiny(name):
    for suf in NO_SHINY:
        if name == suf:
            return True
    return False

def is_mega(name):
    for suf in MEGA_SUFFIX:
        if name.endswith(suf):
            return True
    return False

def is_gmax(name):
    for suf in GMAX_SUFFIX:
        if name.endswith(suf):
            return True
    return False

index_map = get_pokemon_index()
evo_chains = utils.load_evo_chains()

_, all_moves_users = utils.load_all_moves()

def findBaseName(entry, species, old_pokedex):
        base_name = entry.name
        found = False
        for suff in MEGA_SUFFIX:
            if base_name.endswith(suff):
                base_name = base_name.removesuffix(suff)
                found = True
                break
        if not found:
            for suff in GMAX_SUFFIX:
                if base_name.endswith(suff):
                    base_name = base_name.removesuffix(suff)
                    found = True
                    break
        base_name = find_old_name(base_name, species, old_pokedex)
        found = found and base_name in old_pokedex
        return found, base_name

# This class is a mirror of the json data structure that pokecube uses for loading
class PokedexEntry:
    def __init__(self, forme, species) -> None:
        self.init_simple(forme, species)
        self.init_stats(forme)
        self.init_types(forme)
        self.init_abilities(forme)
        self.init_moves(forme)

    # Presently this just sets the models
    def add_models(self, models):
        self.models = models

    # Post processes converting old evolutions, to convert the name and evo move names
    def post_process_evos(self, forme, species):
        if 'forme_items' in self.__dict__:
            for evo in self.forme_items:
                # ones that change model don't have this, so we skip
                if not 'forme' in evo:
                    continue
                # Ensure name is updated.
                name = evo['forme']
                new_name = find_new_name(name, index_map.keys())
                if new_name is None:
                    print(f'unknown evo: {name}')
                else:
                    evo['forme'] = new_name
        added_evos = []
        if 'evolutions' in self.__dict__:
            for evo in self.evolutions:
                name = evo['name']
                new_name = find_new_name(name, index_map.keys())
                if new_name is None:
                    print(f'unknown evo: {name}')
                else:
                    evo['name'] = new_name
                added_evos.append(new_name)
                if 'evoMoves' in evo:
                    args = evo['evoMoves'].split(',')
                    moves = []
                    for move in args:
                        name = convert_old_move_name(move)
                        if name is not None:
                            moves.append(name)
                    if len(moves) > 0:
                        evo['evoMoves'] = str(moves).replace('[', '').replace(']', '').replace("'", '')
                    pass
                if 'move' in evo:
                    move = evo['move']
                    evo['move'] = convert_old_move_name(move)
        

        if self.name in evo_chains:
            evos = evo_chains[self.name]
            no_evos = False
            if not 'evolutions' in self.__dict__:
                self.evolutions = []
                no_evos = True

            for item in evos:
                evo_to = item['name']
                evo_details = item['evolution_details']
                if len(evo_details) == 0:
                    continue
                # We only process first one, if you need to do more, manually add
                # the first one is the "normal" evolution, further ones
                # are region specific, with no details in the file as to which region...
                evo_details = evo_details[0]

                if not evo_to in added_evos and no_evos:
                    valid = False
                    new_evo = {}
                    new_evo['name'] = evo_to
                    if evo_details["min_level"] is not None:
                        new_evo["level"] = evo_details["min_level"]
                        valid = True
                    if evo_details["known_move"] is not None and "/api/v2/move/" in evo_details["known_move"]["url"]:
                        new_evo["move"] = evo_details["known_move"]["name"]
                        valid = True

                    if evo_to in evo_moves:
                        new_evo["evoMoves"] = evo_moves[evo_to]

                    if valid:
                        self.evolutions.append(new_evo)
                    else:
                        pass
                        # print(f"Unable to auto-generate evolution to {evo_to} for {self.name}")
            if len(self.evolutions) == 0:
                del self.evolutions
                    

    # Basic set of initialising, covering names, happiness, etc
    def init_simple(self, forme, species):
        self.name = entry_name(forme.name)
        self.names = species.names
        self.id = forme.id
        self.stock = True
        if not forme.is_default and is_extra_form(self.name):
            self.is_extra_form = True
        if no_shiny(self.name):
            self.no_shiny = True
        self.base_experience = forme.base_experience
        if self.base_experience is not None:
            if not self.name in base_exp_fixes:
                base_exp_fixes[self.name] = self.base_experience + 30
        if self.base_experience is None:
            _basename = species.name
            if self.name in MEGA_BASE_MAP:
                _basename = MEGA_BASE_MAP[self.name]
            if self.name in base_exp_fixes:
                self.base_experience = base_exp_fixes[self.name]
            elif _basename in base_exp_fixes:
                self.base_experience = base_exp_fixes[_basename]
            elif WARN_NO_EXP:
                print("Error, no base exp for "+self.name+f" {_basename}")

        # These values are reported as 10x the value in the games for some reason.
        self.size = {'height': forme.height/10.0}
        self.mass = forme.weight/10.0

        self.is_default = forme.is_default
        self.capture_rate = species.capture_rate

        if 'base_happiness' in species.__dict__ and species.base_happiness != None:
            self.base_happiness = species.base_happiness
        else:
             self.base_happiness = 70
        self.growth_rate = species.growth_rate.name

        gender = species.gender_rate

        # Convert gender rate to the format pokecube uses
        if gender == 0:
            self.gender_rate = 0
        elif gender == 1:
            self.gender_rate = 30
        elif gender == 2:
            self.gender_rate = 62
        elif gender == 4:
            self.gender_rate = 127
        elif gender == 6:
            self.gender_rate = 191
        elif gender == 7:
            self.gender_rate = 225
        elif gender == 8:
            self.gender_rate = 254
        else:
            self.gender_rate = 255

    # Initialise the stats and EV yields
    def init_stats(self, forme):
        self.stats = {}
        self.evs = {}
        for stat in forme.stats:
            name = stat.stat.name
            name = name.replace('-', '_')
            self.stats[name] = stat.base_stat
            if stat.effort!=0:
                self.evs[name] = stat.effort

    # Initialises the array of _types
    def init_types(self, forme):
        self.types = []
        for _type in forme.types:
            name = _type.type.name
            name = name.replace('-', '_')
            if not name in self.types:
                self.types.append(name)

    # Initialises the normal and hidden abilities
    def init_abilities(self, forme):
        normal = []
        hidden = []
        abilities = {}
        for ability in forme.abilities:
            name = ability.ability.name
            if ability.is_hidden:
                hidden.append(name)
            else:
                normal.append(name)
        if len(normal) > 0:
            abilities['normal'] = normal
        if len(hidden) > 0:
            abilities['hidden'] = hidden
        if len(abilities) > 0:
            self.abilities = abilities 

    # Initialises movesets
    def init_moves(self, forme):
        moves = {}
        level_up = []
        misc = []
        all_moves = []

        move_levels = {}

        # Used to check if learn method is level up.
        def is_levelup(details):
            return details.move_learn_method.name == 'level-up'
        
        for move in forme.moves:
            name = move.move.name

            # See if level up data exists, default means using USUM movesets, as are most complete
            level_up_details = default_or_latest(move.version_group_details, is_levelup)

            # If we have such movesets, use them
            if level_up_details is not None:
                level = level_up_details.level_learned_at
                entry = {
                    'L':level,
                    'moves': []
                }
                key = str(level)
                if key in move_levels:
                    entry = move_levels[key]
                else:
                    move_levels[key] = entry
                    level_up.append(entry)
                entry['moves'].append(name)
                all_moves.append(name)

            # All other moves get added to misc moves for TMs in pokecube
            for details in move.version_group_details:
                if details == level_up_details:
                    continue
                if not name in misc:
                    misc.append(name)
                    all_moves.append(name)

        
        if forme.name in all_moves_users:
            _moves = all_moves_users[forme.name]
            for move in _moves:
                if not move in all_moves:
                    misc.append(move)

        # Add the moves if we found any
        if len(level_up) > 0:
            moves['level_up'] = level_up
        if len(misc) > 0:
            moves['misc'] = misc

        if len(moves) > 0:
            self.moves = moves

class PokemonSpecies:
    def __init__(self, species, old_pokedex, overrides) -> None:
        self.species = species
        self.species_id = species.id

        numbers = []
        default = -1

        # Varieties in here are what we register as pokedex entries
        for value in species.varieties:
            if isIgnored(value.pokemon.name):
                continue
            id = url_to_id(value.pokemon)
            if value.is_default:
                default = id
            numbers.append(id)

        base = get_pokemon(default)
        numbers.remove(default)
        self.formes = []
        self.formes.append(base)
        for id in numbers:
            forme = get_pokemon(id)
            if forme is None:
                print(f'error with form {id} for {species.name}')
            else:
                self.formes.append(forme)

        added = []

        self.names = []
        self.entries = []

        # Makes the pokedex entry for each one
        for forme in self.formes:
            entry = PokedexEntry(forme, species)

            model_name = to_model_form(forme.name, species, old_pokedex)
            if(model_name is not None):
                # We need to handle this to the older model added?
                continue

            # Now replace things with custom overrides.
            if entry.name in overrides:
                var = overrides[entry.name]
                for var_key, var_val in var.items():
                    if (isinstance(var_val, list) or isinstance(var_val, map)) and len(var_val) == 0:
                        var_val = None
                    if var_val is not None:
                        entry.__dict__[var_key] = var_val

            # Check if we need to convert anything over from old ones
            old_name = find_old_name(forme.name, species, old_pokedex)
            if(old_name is not None):

                # Some things get merged, like the meteor miniors, so skip duplicates
                if(old_name in added):
                    # Only log new cases of this
                    if not "minior-meteor" in old_name:
                        print(f'Skipping duplicate {old_name} -> {entry.name}')
                    continue

                old_entry = old_pokedex[old_name]
                added.append(old_name)

                # Copy old model info over
                if 'model' in old_entry:
                    model = old_entry['model']
                    key = model['key']
                    entry.model = process_model(entry, key, model)
                if 'male_model' in old_entry:
                    model = old_entry['male_model']
                    key = model['key']
                    entry.male_model = process_model(entry, key, model)
                if 'female_model' in old_entry:
                    model = old_entry['female_model']
                    key = model['key']
                    entry.female_model = process_model(entry, key, model)
                if 'interactions' in old_entry:
                    entry.interactions = old_entry['interactions']
                if 'prey' in old_entry:
                    entry.prey = old_entry['prey']
                if 'models' in old_entry:
                    models = [m for m in old_entry['models']]
                    for model in models:
                        key = model['key']
                        process_model(entry, key, model)
                    entry.add_models(models)
                elif len(forme.forms) > 1:
                    models = []
                    # Automatically make and add models for each forme if multiple
                    for form in forme.forms:
                        name = form.name

                        if banned_form(name):
                            continue

                        id = url_to_id(form)
                        form = get_form(id)
                        key = name
                        model = {
                            'key': key,
                            'tex': key,
                            'model': key,
                            'anim': key,
                        }
                        # Process any changes needed, like for arceus,silvally,etc
                        process_model(entry, key, model)

                        _types = ''
                        for _type in form.types:
                            _types = _types + ' '+ _type.type.name
                        _types = _types.strip().replace(' ', ',')
                        if len(_types) > 0:
                            model['types'] = _types

                        if form.is_default:
                            entry.model = model
                        else:
                            models.append(model)
                    if len(models) > 0:
                        entry.add_models(models)
            elif WARN_NO_OLD_ENTRY:
                print(f'"{entry.name}" : "",')

            # Now delete things from custom overrides.
            if entry.name in overrides:
                var = overrides[entry.name]
                for var_key, var_val in var.items():
                    if (isinstance(var_val, list) or isinstance(var_val, dict)) and len(var_val) == 0:
                        var_val = None
                    if var_val is None and var_key in entry.__dict__:
                        print(f'deleting {var_key} for {entry.name}')
                        del entry.__dict__[var_key]
                    elif var_val is not None:
                        entry.__dict__[var_key] = var_val

            found, base_name = findBaseName(entry, species, old_pokedex)
            if found:
                _entry = old_pokedex[base_name]
                if len(entry.evs) == 0:
                    entry.evs = _entry["evs"]
                if "loot_table" in _entry and not hasattr(entry, "loot_table"):
                    entry.loot_table = _entry["loot_table"]
                if "sound" in _entry and not hasattr(entry, "sound"):
                    entry.sound = _entry["sound"]
            

            # Print an error if we think it should have had moves, but has none
            no_moves = (not 'moves' in entry.__dict__ or not 'level_up' in entry.moves)
            if no_moves:
                if found:
                    _entry = old_pokedex[base_name]
                    found = not (not 'moves' in _entry or not 'level_up' in _entry["moves"])
                    if found:
                        entry.moves = _entry["moves"]
                if not found:
                    print(f'No moves for {entry.name}, {base_name}??')
            # Now cleanup evolutions
            entry.post_process_evos(forme, species)

            entry.id = default

            self.entries.append(entry)
            self.names.append(entry.name)

def convert_tags(entries):

    def is_pokemob_tag(file):
        return not "pokemob_moves" in file

    jsons = [y for x in os.walk("./old/tags") for y in glob(os.path.join(x[0], '*.json'))]
    for file in jsons:
        json_in = open(file, 'r', encoding='utf-8')
        json_str = json_in.read()
        json_in.close()
        json_obj = json.loads(json_str)
        if 'values' in json_obj:
            old_values = json_obj['values']
            new_values = []
            for name in old_values:
                add = ''
                if ';' in name:
                    vars = name.split(';')
                    name = vars[0]
                    add = f';{vars[1]}'
                orig = name
                if name.startswith("pokecube:"):
                    name = name.replace('pokecube:', '')
                if name in TAG_IGNORE:
                    continue
                new_name = find_new_name(name, index_map.keys())
                if new_name in TAG_IGNORE:
                    continue

                if "entity_types" in file:
                    if new_name in entries:
                        var = entries[new_name]
                        if(hasattr(var, "is_extra_form")):
                            continue
                    if name in entries:
                        var = entries[name]
                        if(hasattr(var, "is_extra_form")):
                            continue

                if new_name is not None:
                    if not ":" in new_name:
                        new_name = f'pokecube:{new_name}{add}'
                    if not new_name in new_values:
                        new_values.append(new_name)
                elif 'arceus_' in name or 'silvally_' in name:
                    pass
                else:
                    if not "#" in name and not ":" in name and name != 'egg' and is_pokemob_tag(file):
                        print(f"error finding name for {name} in {file}")
                    if not ":" in orig and is_pokemob_tag(file):
                        new_name = f'pokecube:{orig}{add}'
                    else:
                        new_name = orig
                    if not new_name in new_values:
                        new_values.append(new_name)
            json_obj['values'] = new_values

        filename = file.replace('./old', TAG_DATA_DIR)
        if not os.path.exists(os.path.dirname(filename)):
            os.makedirs(os.path.dirname(filename))
        dump_file(json_obj, filename)

        if "entity_types" in filename:
            filename = filename.replace('entity_types', "entity_type")
            if not os.path.exists(os.path.dirname(filename)):
                os.makedirs(os.path.dirname(filename))
            dump_file(json_obj, filename)

        if "creature_types" in filename:
            filename = filename.replace('creature_types', "creature_type")
            if not os.path.exists(os.path.dirname(filename)):
                os.makedirs(os.path.dirname(filename))
            dump_file(json_obj, filename)

def load_overrides(override_file, overrides):
    override = f'./data/pokemobs/{override_file}.json'
    file = open(override, 'r')
    data = file.read()
    file.close()
    _override = json.loads(data)
    for entry in _override:
        name = entry['name']
        if not name in overrides:
            overrides[name] = {}
        for key, value in entry.items():
            if key == 'name':
                continue
            overrides[name][key] = value

def convert_mega_rules(entry):
    if not "mega_rules" in entry:
        return
    if not os.path.exists(mega_rule_dir):
        os.makedirs(mega_rule_dir)
    file = f'{mega_rule_dir}{entry["name"]}.json'
    if os.path.exists(file):
        # Let's not auto-replace these either.
        del entry["mega_rules"]
        return
    rules = []
    for rule in entry["mega_rules"]:
        _rule = {}
        name = "???"
        user = entry["name"]
        da_rule = {}
        da_rule['key'] = 'item'

        if 'preset' in rule and 'item_preset' in rule:
            key = rule['preset']
            item = rule['item_preset']
            if not ":" in item:
                item = f"pokecube:{item}"
            da_rule["item"] = {"item":item}
            name = f'{user}-{key.lower()}'
            name = find_new_name(name, index_map.keys())
        elif "name" in rule:
            name = rule['name']
            name = find_new_name(name, index_map.keys())
            if "move" in rule:
                move = convert_old_move_name(rule['move'])
                da_rule["move"] = move
                da_rule['key'] = "move"
            elif 'item_preset' in rule:
                item = rule['item_preset']
                if not ":" in item:
                    item = f"pokecube:{item}"
                da_rule["item"] = {"item":item}
            elif 'ability' in rule:
                da_rule['key'] = 'ability'
                da_rule["ability"] = rule['ability']

        _rule['user'] = user
        _rule['name'] = name
        _rule['rule'] = da_rule

        rules.append(_rule)
        
    if(len(rules) == 1):
        rules = rules[0]
    dump_file(rules, file)
    del entry["mega_rules"]

def convert_evolution(entry):
    if not "evolutions" in entry:
        return
    if not os.path.exists(evos_rule_dir):
        os.makedirs(evos_rule_dir)

    rules = []

    file = f'{evos_rule_dir}{entry["name"]}.json'
    if os.path.exists(file):
        # Let's not override these, let them be manually defined if needed
        del entry["evolutions"]
        return

    for rule in entry["evolutions"]:
        _rule = {}

        # First lets get the user and the result
        result = rule["name"]
        user = entry["name"]

        # Now we construct the rules
        da_rules = []

        # Level rule
        if "level" in rule:
            sub_rule = {"key": "level"}
            sub_rule["level"] = rule["level"]
            da_rules.append(sub_rule)

        # Location specific things
        location = {}
        if "location" in rule:
            location = rule["location"]
        if "time" in rule:
            matchs = {}
            if "matchers" in location:
                matchs = location['matchers']
            matchs['time'] = {"preset": rule["time"]}
            location['matchers'] = matchs
        if "rain" in rule:
            matchs = {}
            if "matchers" in location:
                matchs = location['matchers']
            weather = "rain" if rule["rain"] else "sun"
            matchs['weather'] = {"type": weather}
            location['matchers'] = matchs
        if len(location) > 0:
            sub_rule = {"key": "location"}
            sub_rule["location"] = location
            da_rules.append(sub_rule)

        # Required items
        if 'item_preset' in rule:
            sub_rule = {"key": "item"}
            item = rule['item_preset']
            if not ":" in item:
                item = f"pokecube:{item}"
            sub_rule["item"] = {"item":item}
            da_rules.append(sub_rule)
        elif 'item' in rule:
            item = rule["item"]["values"]
            sub_rule = {"key": "item"}
            sub_rule["item"] = item
            da_rules.append(sub_rule)

        # Traded
        if "trade" in rule:
            sub_rule = {"key": "traded"}
            da_rules.append(sub_rule)

        # Happiness needed
        if "happy" in rule:
            sub_rule = {"key": "happy"}
            da_rules.append(sub_rule)

        # Sexe needed
        if "sexe" in rule:
            sub_rule = {"key": "sexe"}
            sub_rule["sexe"] = rule["sexe"]
            da_rules.append(sub_rule)

        # Move needed
        if "move" in rule:
            sub_rule = {"key": "move"}
            sub_rule["move"] = rule["move"]
            da_rules.append(sub_rule)

        # Random Chance needed
        if "chance" in rule:
            sub_rule = {"key": "chance"}
            sub_rule["chance"] = rule["chance"]
            da_rules.append(sub_rule)

        # Specific model needed
        if "form_from" in rule:
            user = rule["form_from"]

        if len(da_rules) == 1:
            da_rules = da_rules[0]

        # Now construct the evolution
        _rule['name'] = result
        _rule['user'] = user
        # Order priority if present
        if "priority" in rule:
            _rule["priority"] = rule["priority"]
        _rule["condition"] = da_rules
        if "evoMoves" in rule:
            _rule["evoMoves"] = rule["evoMoves"]
        if "animation" in rule:
            _rule["animation"] = rule["animation"]
        if "model" in rule:
            _rule["model"] = rule["model"]

        rules.append(_rule)

    if(len(rules) == 1):
        rules = rules[0]
    dump_file(rules, file)
    del entry["evolutions"]

def convert_pokedex():
    pokedex = {}
    for filename in os.listdir(entry_generate_dir):
        with open(f"{entry_generate_dir}/{filename}", 'r') as file:
            entry = json.load(file)
            pokedex[entry['name']] = entry
    overrides = {}

    load_overrides('custom_movesets', overrides)
    load_overrides('custom_sizes', overrides)
    load_overrides('custom_forme_changes', overrides)
    load_overrides('custom_misc', overrides)
    load_overrides('custom_dyeable', overrides)
    load_overrides('custom_models', overrides)
    load_overrides('custom_evolutions', overrides)
    load_overrides('custom_interactions', overrides)

    tables = './data/pokemobs/loot_tables.json'
    file = open(tables, 'r')
    data = file.read()
    file.close()
    _loot_tables = json.loads(data)
    tables = './data/pokemobs/held_tables.json'
    file = open(tables, 'r')
    data = file.read()
    file.close()
    _held_tables = json.loads(data)

    loot_tables = {}
    for key, list in _loot_tables.items():
        for name in list:
            loot_tables[name] = key
    held_tables = {}
    for key, list in _held_tables.items():
        for name in list:
            held_tables[name] = key

    i = 1
    values = get_species(i)
    species = []
    dex = []
    named_entries = {}

    lang_files = {}

    # Initialise this with missingno.
    pokemob_tag_names = ["pokecube:missingno"]

    while values is not None:
        entry = PokemonSpecies(values, pokedex, overrides)
        species.append(entry)
        for var in entry.entries:
            named_entries[var.name] = var
            tag_name = f'pokecube:{var.name}'
            if var.is_default and hasattr(var, "is_extra_form"):
                del var.is_extra_form
            if not tag_name in pokemob_tag_names and not hasattr(var, "is_extra_form"):
                pokemob_tag_names.append(tag_name)

            if var.name in held_tables:
                var.held_table = held_tables[var.name]
            if var.name in loot_tables:
                var.loot_table = loot_tables[var.name]

            for name in var.names:
                _name = name.name
                lang = utils.get('language', url_to_id(name.language))
                key = f'{lang.iso639}_{lang.iso3166}.json'
                items = {}
                if key in lang_files:
                    items = lang_files[key]
                items[f"entity.pokecube.{var.name}"] = _name
                lang_files[key] = items
            del var.names

            dex.append(var.__dict__)
        i = i + 1
        values = get_species(i)

    # Now lets handle anything defined as a "custom entry"
    custom = './data/pokemobs/custom_entries.json'
    file = open(custom, 'r')
    data = file.read()
    file.close()
    custom = json.loads(data)
    for var in custom:
        tag_name = f'pokecube:{var["name"]}'
        if not tag_name in pokemob_tag_names:
            pokemob_tag_names.append(tag_name)
        if "names" in var:
            for name in var["names"]:
                _name = name["name"]
                _id = int(name["language"]['url'].split('/')[-2])
                lang = utils.get('language', _id)
                key = f'{lang.iso639}_{lang.iso3166}.json'
                items = {}
                if key in lang_files:
                    items = lang_files[key]
                items[f"entity.pokecube.{var['name']}"] = _name
                lang_files[key] = items
            del var['names']

        dex.append(var)

    for key, dict in lang_files.items():
        # Output a lang file for the entries
        file = f'{mob_lang_generate_dir}{key}'
        if not os.path.exists(os.path.dirname(file)):
            os.makedirs(os.path.dirname(file))
        try:
            dump_file(dict, file, encoding="utf-8", ensure_ascii=False)
        except Exception as err:
            print(f'error saving for {key}')
            print(err)

    for var in dex:
        # Some extra pre-processing
        convert_mega_rules(var)
        convert_evolution(var)
        # Output each entry into the appropriate database location
        file = f'{entry_generate_dir}{var["name"]}.json'
        if not os.path.exists(os.path.dirname(file)):
            os.makedirs(os.path.dirname(file))

        dump_file(var, file)

        # Now lets make a template file which will remove each entry.
        if UPDATE_EXAMPLE:
            file = f'../../example_datapacks/_removal_template_/data/pokecube_mobs/database/pokemobs/pokedex_entries/{var["name"]}.json'
            var = {"remove": True,"priority":0}
            if not os.path.exists(os.path.dirname(file)):
                os.makedirs(os.path.dirname(file))
            dump_file(var, file)
    for file in os.listdir('./data/pokemobs/materials'):
        original = f'./data/pokemobs/materials/{file}'
        newfile = f'{materials_generate_dir}{file}'
        if not os.path.exists(os.path.dirname(newfile)):
            os.makedirs(os.path.dirname(newfile))
        shutil.copy(original, newfile)

    return named_entries

def make_ability_langs():
    ability_index = utils.get_valid_numbers('ability')

    lang_files = {}

    for name, number in ability_index.items():
        var = utils.get('ability', number)
        for name in var.names:
            _name = name.name
            lang = utils.get('language', url_to_id(name.language))
            key = f'{lang.iso639}_{lang.iso3166}.json'
            items = {}
            if key in lang_files:
                items = lang_files[key]
            items[f"ability.{var.name}.name"] = _name
            lang_files[key] = items

    for key, dict in lang_files.items():
        # Output a lang file for the entries
        file = f'{ability_lang_generate_dir}{key}'
        if not os.path.exists(os.path.dirname(file)):
            os.makedirs(os.path.dirname(file))
        try:
            dump_file(dict, file, encoding="utf-8", ensure_ascii=False)
        except Exception as err:
            print(f'error saving for {key}')
            print(err)

if __name__ == "__main__":
    entries = convert_pokedex()
    convert_tags(entries)
    make_ability_langs()
