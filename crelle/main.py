from pathlib import Path
import yaml
import itertools


LANGUAGES = {
    'eng': 'english',
    'nor': 'norwegian'
}

PROBLEM_NAMES = {
    'eng': 'problem',
    'nor': 'oppgave',
}

SOLUTION_NAMES = {
    'eng': 'solution',
    'nor': 'løsning',
}

DEFAULT_LANG = 'eng'
CRELLE_DB = Path(r'/home/karlerik/Data/hobby/crelledb')
TEMPLATE_SUBDIR = 'templates'
PROBLEM_SUBDIR = 'problems'
prob = 'chesscorners.yaml'
TEMPLATE = Path(CRELLE_DB) / 'simpletemplate.tex'

packagename = 'amsmath'
STANDARD_PREAMBLE = '\\usepackage[utf8]{inputenc}\n' + '\n'.join(
    [f'\\usepackage{{{packagename}}}'
     for packagename in ['amsmath', 'amssymb', 'graphicx']]
)

def parse_prob(prob):
    p = Path(CRELLE_DB) / PROBLEM_SUBDIR / Path(prob)
    with open(p) as f:
        return Problem(yaml.safe_load(f), DEFAULT_LANG)



class Text(dict):
    # stuff intended to be okay basically wherever in Crelle.
    # can occur either as just a string, in which case it is presumed default_lang,
    # or as a dict {nor: text in norwegian, eng: text in english, ...}.
    # text can also, instead of a string, be a list of strings.
    # the meaning of this depends on context - for a problem, each element
    # is presumed to be a subproblem, with the first element being general
    # text applying to all subproblems, for tags, each element is a tag.

    def __init__(self, yaml_dict, default_lang):
        super().__init__()

        if type(yaml_dict) is not dict:
            yaml_dict = {default_lang: yaml_dict}

        assert len({type(v) for v in yaml_dict.values()}) == 1

        for lang, text in yaml_dict.items():
            self[lang] = text


class Problem:
    def __init__(self, yaml_dict, default_lang):
        required_keys = {
            'tags', 'source', 'problem'
        }
        optional_keys = {
            'dependencies', 'preamble', 'solution'
        }

        assert all([k in yaml_dict for k in required_keys])
        assert set(yaml_dict.keys()).issubset(required_keys.union(optional_keys))

        self.tags = yaml_dict['tags']
        self.source = Text(yaml_dict['source'], default_lang)
        self.problemtext = Text(yaml_dict['problem'], default_lang)
        self.solution = Text(yaml_dict.get('problem', {}), default_lang)
        self.dependencies = yaml_dict.get('dependencies', [])
        self.preamble = yaml_dict.get('preamble', '')

    def __repr__(self):
        return super().__repr__()


def load_problem(problem_path, language):
    if type(problem_path) is not str:
        assert type(problem_path) is dict
        return problem_path[language]

    with open(CRELLE_DB / PROBLEM_SUBDIR / problem_path) as f:
        data = yaml.load(f)

    problem_text = data['problem'][language]
    solution_text = data.get('solution', {}).get(language, '')
    deps = data.get('dependencies', [])
    source = data.get('source', '')


    return {'probtext': problem_text,
            'soltext': solution_text,
            'deps': deps,
            'source': source,
            'preamble': data.get('preamble', ''),
            'orig_path': problem_path}
    
def render_source(sourcetext, lang):
    if sourcetext == 'classical':
        return ''
    if type(sourcetext) is dict:
        return sourcetext[lang]
    else:
        datadict = {
            'classical': {'nor': 'klassisk'},
        }
        s = datadict.get(sourcetext, {}).get(lang)
        if s:
            return s.title()
        else:
            return sourcetext



def make_set_tex(set_config_path, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    with open(set_config_path) as f:
        config = yaml.load(f)

    for k in ['template', 'language', 'problems']:
        assert k in config, f'Key {k} required'

    lang = config['language']
    with open(CRELLE_DB / TEMPLATE_SUBDIR / config['template']) as f:
        template = f.read()

    assert type(config['problems']) is list, 'problems key should be a list'

    problem_paths = config['problems']
    problem_data = [load_problem(p, lang) for p in problem_paths]

    for dep in itertools.chain(*[
            p['deps'] for p in problem_data if type(p) is dict
    ]):
        (Path(out_dir) / dep).write_bytes(
            (CRELLE_DB / PROBLEM_SUBDIR / dep).read_bytes()
        )

    preamble = STANDARD_PREAMBLE + '\n'.join(
        [p['preamble'] + f"% {p['orig_path']}"
         for p in problem_data if type(p) is dict and p.get('preamble')]
    )

    text = ''
    for p in problem_data:
        if type(p) is str:
            # just insert p as is
            text += '\n' + p + '\n'
            continue
        
        source = render_source(p['source'], lang)
        probtext = p['probtext']
        text += '\n% ' + p['orig_path'] + '\n'
        text += f'\\begin{{cproblem}}{{{source}}}\n{probtext}\n\\end{{cproblem}}\n'

        if config.get('solutions') and p.get('soltext'):
            soltext = p['soltext']
            text += f'\\begin{{csolution}}\n{soltext}\n\\end{{csolution}}'


    template = template.replace('{{{probname}}}', PROBLEM_NAMES[lang].title())
    template = template.replace('{{{solname}}}', SOLUTION_NAMES[lang].title())
    template = template.replace('{{{preamble}}}', preamble)
    template = template.replace('{{{problems}}}', text)

    with open(Path(out_dir) / 'problem_set.tex', 'w') as f:
        f.write(template)
    return lang
    
s = make_set_tex('combday1.yaml', 'outdir')

