#!/bin/env python3
# build a monster table for the game, using a csv spreadsheet

import sys
import yaml

def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <source-tsv> <output-yaml>")
        exit(1)

    monsters = []
    envs = set()
    with open(sys.argv[1]) as f:
        headers = f.readline().strip().split("\t")
        for l in f.readlines():
            cols = l.split("\t")
            m = {}
            for h in headers:
                m[h] = cols.pop(0).strip()
                if h != 'name':
                    m[h] = m[h].strip().lower()           
            m['page'] = int(m['page'])
            if m['environment'].strip() == "":
                m['environment'] = []
            else:
                e = []
                for x in m['environment'].split(','):
                    if x == '':
                        continue
                    x = x.strip()
                    envs.add(x)
                    e.append(x)
                m['environment'] = e
            if m['flags'].strip() == '':
                m['flags'] = []
            else:
                m['flags'] = [x for x in m['flags'].split(',')]
            monsters.append(m)    

    # fix up the environments:  if it is 'any', then replace it with
    # all of them!
    for m in monsters:
        if 'any' in m['environment']:
            m['environment'] = list(envs)

    with open(sys.argv[2], 'w') as f:
        yaml.safe_dump({'monsters': monsters}, f)


if __name__ == "__main__":
    main()