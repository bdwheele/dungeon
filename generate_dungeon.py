#!/bin/env python3

import yaml
import sys
import logging
from pathlib import Path
import argparse
import tempfile
import subprocess
import io
import base64

from dungeon.dungeon import Dungeon
from dungeon.tables import Tables
from dungeon.monster import MonsterStore

logger = logging.getLogger()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", default=False, action="store_true", help="Turn on debugging")
    parser.add_argument("--style", default="default", help="Dungeon style to use")

    subparsers = parser.add_subparsers(help="commands", dest="cmd")    
    generate_cmd = subparsers.add_parser("generate", help="Generate a dungeon")
    generate_cmd.add_argument("dungeon", metavar="<dungeon>", help="Dungeon file")
    generate_cmd.add_argument("--room_count", type=int, default=10, help="Number of rooms/corridors")
    generate_cmd.add_argument("--character_levels", default="1,1,1,1", help="Comma-separated list of character levels")
    generate_cmd.add_argument("--monster_sources", default=None, help="Comma-separated list of monster sources")
    generate_cmd.add_argument("--monster_types", default=None, help="Comma-separated list of monster types")
    generate_cmd.add_argument("--monster_alignments", default=None, help="Comma-separated list of monster alignments")


    generate_cmd.add_argument("--encounter_average_difficulty", default='medium', choices=['easy', 'medium', 'hard', 'deadly'], help="Average encounter difficulty")
    generate_cmd.add_argument("--encounter_room_percent", default=25, type=int, help="Percentage of rooms with an encounter")
    generate_cmd.add_argument("--wandering_monsters", default=6, type=int, help="Number of random wandering monsters to generate")

    regen_cmd = subparsers.add_parser("regen", help="Regenerate part of a dungeon")
    regen_cmd.add_argument("dungeon", metavar="<dungeon>", help="Dungeon file")

    render_cmd = subparsers.add_parser("render", help="Render a dungeon")
    render_cmd.add_argument('--neato-cmd', default='/usr/bin/neato', help='Location of Graphviz neato command')
    render_cmd.add_argument('--all', default=False, action="store_true", help="Render bits even if not visited")
    render_cmd.add_argument("dungeon", metavar="<dungeon>", help="Dungeon file")
    render_cmd.add_argument('what', metavar='<what>', choices=['map', 'tree'], help='What to render')
    render_cmd.add_argument('output', metavar='<output>', help='render output file / directory')    

    encounter_cmd = subparsers.add_parser("encounter", help="Generate an ecounter")
    encounter_cmd.add_argument("--character_levels", default="1,1,1,1", help="Comma-separated list of character levels")
    encounter_cmd.add_argument("--monster_sources", default=None, help="Comma-separated list of monster sources")
    encounter_cmd.add_argument("--monster_environments", default=None, help="Comma-separted list of monster environments")
    encounter_cmd.add_argument("--monster_types", default=None, help="Comma-separated list of monster types")
    encounter_cmd.add_argument("--monster_alignments", default=None, help="Comma-separated list of monster alignments")
    encounter_cmd.add_argument("--encounter_difficulty", default='medium', choices=['easy', 'medium', 'hard', 'deadly'], help="Encounter difficulty:  easy, medium, hard, deadly")


    args = vars(parser.parse_args())
    if args['cmd'] is None:
        parser.print_help()
        exit(1)

    # set up logging
    if args['debug']:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)
    log_handler =logging.StreamHandler(sys.stderr)
    log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    log_handler.setFormatter(log_formatter)
    logger.addHandler(log_handler)

    tables_dir = Path(Path(__file__).absolute().parent, 'tables')
    tables = Tables(tables_dir, style=args['style'])


    if args['cmd'] == 'generate':
        dungeon = Dungeon.generate(tables, 
                         room_count=args['room_count'],
                         character_levels=[int(x) for x in args['character_levels'].split(',')],
                         monster_sources=[] if args['monster_sources'] is None else [x.lower() for x in args['monster_sources'].split(',')],
                         monster_alignments=[] if args['monster_alignments'] is None else [x.lower() for x in args['monster_alignments'].split(',')],
                         monster_types= [] if args['monster_types'] is None else [x.lower() for x in args['monster_types'].split(',')],
                         encounter_average_difficulty={'easy': MonsterStore.EASY, 
                                                       'medium': MonsterStore.MEDIUM, 
                                                       'hard': MonsterStore.HARD, 
                                                       'deadly': MonsterStore.DEADLY}[args['encounter_average_difficulty']],
                         encounter_room_percent=args['encounter_room_percent'],
                         wandering_monsters=args['wandering_monsters'])



        with open(args['dungeon'], 'w') as f:
            yaml.dump(dungeon, stream=f, sort_keys=False)

        # for debugging, let's make sure we can load the damned thing
        print("Loading dungeon")
        with open(args['dungeon']) as f:
            dungeon = yaml.load(f)
        print(dungeon)


    elif args['cmd'] == 'regen':
        pass


    elif args['cmd'] == 'render':
        tables = Tables(tables_dir, style=args['style'])
        with open(args['dungeon'], 'r') as f:
            dungeon = yaml.load(f)
        if args['what'] == 'map':
            dot = dungeon.generate_map_dot(all_rooms=args['all'])
            subprocess.run([args['neato_cmd'], '-Tsvg', '-o', args['output']], input=dot.encode('utf-8'), check=True)
        elif args['what'] == 'tree':
            dot = dungeon.generate_object_graph_dot()
            print(dot)
            subprocess.run([args['neato_cmd'], '-Tsvg', '-o', args['output']], input=dot.encode('utf-8'), check=True)

    elif args['cmd'] == 'encounter':
        party = [int(x) for x in args['character_levels'].split(',')]
        difficulty = {'easy': MonsterStore.EASY,
                      'medium': MonsterStore.MEDIUM,
                      'hard': MonsterStore.HARD,
                      'deadly': MonsterStore.DEADLY}[args['encounter_difficulty'].lower()]
        source_filter = [] if args['monster_sources'] is None else [x.strip().lower() for x in args['monster_sources'].split(',')]
        environment_filter = [] if args['monster_environments'] is None else [x.strip().lower() for x in args['monster_environments'].split(',')]
        type_filter = [] if args['monster_types'] is None else [x.strip().lower() for x in args['monster_types'].split(',')]
        alignment_filter = [] if args['monster_alignments'] is None else [x.strip().lower() for x in args['monster_alignments'].split(',')]


        monster_store = MonsterStore(tables)
        base_monster_list = monster_store.filter(environment_filter=environment_filter,
                                                 alignment_filter=alignment_filter,
                                                 type_filter=type_filter,
                                                 source_filter=source_filter)
        encounter = monster_store.create_encounter(party, difficulty, base_monster_list, 1000)
        for m in encounter:
            print(m)





if __name__ == "__main__":
    main()