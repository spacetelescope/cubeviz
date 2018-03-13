import os
import re
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

SCRIPT_FILE = os.path.join(os.path.dirname(__file__), 'scripts', 'update_cubeviz_test_env_pip')

github_dict = {
        'glue': 'https://github.com/glue-viz/glue/commit/HASH', 
        'spectral_cube': 'https://github.com/radio-astro-tools/spectral-cube/commit/HASH',
        'specviz': 'https://github.com/spacetelescope/specviz/commit/HASH', 
        'cubeviz': 'https://github.com/spacetelescope/cubeviz/commit/HASH', 
        'specutils': 'https://github.com/astropy/specutils/commit/HASH', 
        'astropy': 'https://github.com/astropy/astropy/commit/HASH'
}

def test_update_script():
    # The goal is to read in the update script and make sure each 
    # commit hash is correct. 

    regex = r"(\w*)_hash=\"(.*)\""

    # Load in the script
    with open(SCRIPT_FILE, 'r') as fp:
        lines = fp.readlines()

    matches = re.finditer(regex, '\n'.join(lines))
    for match in matches:
        key, commit_hash = match.groups()
        url = github_dict[key].replace('HASH', commit_hash) 

        req = Request(url)
        try:
            response = urlopen(req)
        except HTTPError as e:
            return_code = e.code
        except URLError as e:
            return_code = 400
        else:
            return_code = 200

        assert return_code == 200

