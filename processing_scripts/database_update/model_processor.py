
def _process_tex_only(entry, key, model):
    model['key'] = key
    model['model'] = entry.name
    model['anim'] = entry.name
    model['tex'] = key

def _process_model_only(entry, key, model):
    model['key'] = key
    model['model'] = key
    model['anim'] = entry.name
    model['tex'] = entry.name

def _process_not_tex(entry, key, model):
    model['key'] = key
    model['model'] = key
    model['anim'] = key
    model['tex'] = entry.name

def _process_full(entry, key, model):
    model['key'] = key
    model['model'] = key
    model['anim'] = key
    model['tex'] = key

def _process_no_custom(entry, key, model):
    model['key'] = key
    model['model'] = entry.name
    model['anim'] = entry.name
    model['tex'] = entry.name

def _process_flabebe_colours(entry, key, model):
    model['key'] = key
    model['model'] = entry.name
    model['anim'] = entry.name
    model['tex'] = entry.name
    print(key)

def _process_arceus_silvally(entry, key, model):
    model['model'] = entry.name
    model['anim'] = key.replace('-', '_')
    model['key'] = key.replace('-', '_')
    model['tex'] = key.replace('-', '_')

def _process_unown(entry, key, model):
    if key.endswith("_qu") or key.endswith("_ex"):
        _process_full(entry, key, model)
    else:
        _process_model_only(entry, key, model)

PROCESSORS = {
    'arceus': _process_arceus_silvally,
    'silvally': _process_arceus_silvally,
    # 'burmy': _process_tex_only,
    'genesect': _process_not_tex,
    'furfrou': _process_no_custom,
    'flabebe': _process_flabebe_colours,
    'floette': _process_flabebe_colours,
    'florges': _process_flabebe_colours,
    'sinistea': _process_model_only,
    'polteageist': _process_model_only,
    'unown': _process_unown,
    'xerneas': _process_tex_only,
}

def process_model(entry, key, model):
    if entry.name in PROCESSORS:
        PROCESSORS[entry.name](entry, key, model)
    return model