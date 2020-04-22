#!/bin/env python3

import yaml
import sys
import logging
from pathlib import Path
import argparse
import tempfile
import subprocess
import io

from dungeon.dungeon import Dungeon
from dungeon.tables import Tables
from dungeon.monster import Encounter

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
    render_cmd.add_argument('--dot-cmd', default='/usr/bin/dot', help='Location of Graphviz dot command')
    render_cmd.add_argument("dungeon", metavar="<dungeon>", help="Dungeon file")
    render_cmd.add_argument('what', metavar='<what>', choices=['map', 'html'], help='What to render')
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
        dungeon = Dungeon()
        dungeon.generate(tables, 
                         room_count=args['room_count'],
                         character_levels=[int(x) for x in args['character_levels'].split(',')],
                         monster_sources=[] if args['monster_sources'] is None else [x.lower() for x in args['monster_sources'].split(',')],
                         monster_alignments=[] if args['monster_alignments'] is None else [x.lower() for x in args['monster_alignments'].split(',')],
                         monster_types= [] if args['monster_types'] is None else [x.lower() for x in args['monster_types'].split(',')],
                         encounter_average_difficulty={'easy': Encounter.EASY, 
                                                       'medium': Encounter.MEDIUM, 
                                                       'hard': Encounter.HARD, 
                                                       'deadly': Encounter.DEADLY}[args['encounter_average_difficulty']],
                         encounter_room_percent=args['encounter_room_percent'],
                         wandering_monsters=args['wandering_monsters'])



        with open(args['dungeon'], 'w') as f:
            yaml.safe_dump(dungeon.save(), stream=f)

    elif args['cmd'] == 'regen':
        pass


    elif args['cmd'] == 'render':
        tables = Tables(tables_dir, style=args['style'])
        with open(args['dungeon'], 'r') as f:
            data = yaml.safe_load(f)
        dungeon = Dungeon.load(data)
        if args['what'] == 'map':        
            dot = dungeon.map.dump_graphviz().encode('utf-8')
            subprocess.run([args['dot_cmd'], '-Tsvg', '-o', args['output']], input=dot, check=True)
        elif args['what'] == 'html':
            output = Path(args['output'])
            if output.exists():
                if output.is_dir():
                    if len(list(output.iterdir())) != 0:
                        print("Directory exists but isn't empty")
                        exit(1)
                else:
                    print("Output exists as a file -- refusing to overwrite")
                    exit(1)
            else:
                output.mkdir()
            dungeon.render_html(output, args['dot_cmd'])

    elif args['cmd'] == 'encounter':
        party = [int(x) for x in args['character_levels'].split(',')]
        difficulty = {'easy': Encounter.EASY,
                      'medium': Encounter.MEDIUM,
                      'hard': Encounter.HARD,
                      'deadly': Encounter.DEADLY}[args['encounter_difficulty'].lower()]
        source_filter = [] if args['monster_sources'] is None else [x.strip().lower() for x in args['monster_sources'].split(',')]
        environment_filter = [] if args['monster_environments'] is None else [x.strip().lower() for x in args['monster_environments'].split(',')]
        type_filter = [] if args['monster_types'] is None else [x.strip().lower() for x in args['monster_types'].split(',')]
        alignment_filter = [] if args['monster_alignments'] is None else [x.strip().lower() for x in args['monster_alignments'].split(',')]

        encounter = Encounter(tables, party, source_filter=source_filter, alignment_filter=alignment_filter,
                              type_filter=type_filter, environment_filter=environment_filter)
        for m in encounter.create_encounter(difficulty):
            print(m.attributes)





if __name__ == "__main__":
    main()