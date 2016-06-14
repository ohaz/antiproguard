import sys
import json
from pprint import pprint
__author__ = 'ohaz'


def dict_compare(dict1, dict2, factor):
    similar = []
    for k, v in dict1.items():
        for nv in range(max(0, v-int(v/factor)), v+int(v/factor)):
            if nv in dict2.values():
                k2 = list(dict2.keys())[list(dict2.values()).index(nv)]
                similar.append((k, k2, v, nv))
    return similar

if __name__ == '__main__':
    with open(sys.argv[1]) as d1_file:
        content = d1_file.read()
        d1 = json.loads(content)
    with open(sys.argv[2]) as d2_file:
        content = d2_file.read()
        d2 = json.loads(content)
    pprint(dict_compare(d1, d2, factor=20))
