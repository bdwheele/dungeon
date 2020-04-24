from yaml import YAMLObject
from .graph import gen_graph
from .door import Door
from .room import Room
from .monster import MonsterStore


#from .map import Map
from pathlib import Path
import subprocess
import math
from .utils import generate_avg_list
import random

# THE DUNGEON!
# The dungeon serves as a container for everything about the dungeon:  the rooms, doors,
# monsters, treasure, etc.  It also contains the information about the game in progress.
#
# 


class Dungeon(YAMLObject):
    """
    The dungeon including everything in it and the current state.
    """
    def __init__(self, **kwargs):
        version = kwargs.get('version')
        if version is None:
            raise ValueError("Cannot create a dungeon with no version!")
        if version == 1:
            # create the prototype object
            self.version = 1
            self.parameters = {}
            self.characters = {}
            self.state = {
                'current_room': 0,
                'current_time': 0
            }
            self.monsters = {}
            self.rooms = {}
            self.doors = {}
            self.traps = {}

            # and then override whatever we got from the kwargs
            for k in vars(self):
                if k in kwargs:
                    setattr(self, k, kwargs[k])
        else:
            raise ValueError(f"Cannot create dungeon version {version}")

    @staticmethod
    def generate(tables, room_count=10, character_levels=[1, 1, 1, 1],
                 monster_sources=['mm'], monster_types=[], monster_alignments=[],
                 encounter_average_difficulty=MonsterStore.MEDIUM,
                 encounter_room_percent=25, wandering_monsters=6): 
        """
        Generate a dungeon based on the parameters given, as well as the parameters
        from the settings/parameters table for the current style.
        """
        args = {'version': 1}
        args['parameters'] = tables.get_table('dungeon', 'parameters')
        edges = gen_graph(room_count, 
                          edge_dist=tables.get_table('graph', 'edges_per_node'),
                          use_existing_node_dist=tables.get_table('graph', 'edge_connect_existing'),
                          edge_distance_dist=tables.get_table('graph', 'edge_distance'))

        # the edges data tells us all of the room ids and how they're
        # connected, but we need to compute the list of edge ids 
        # per node to give context to the room generator.  
        node_edges = {}
        for i, edge in enumerate(edges):
            for node_id in edge:
                if node_id not in node_edges:
                    node_edges[node_id] = []
                node_edges[node_id].append(i)
        # generate the rooms
        args['rooms'] = {}
        for node_id in node_edges:
            args['rooms'][node_id] = Room.generate(tables, node_id, node_edges[node_id])

        # create doors/passages from all of the edges
        args['doors'] = {}
        for i, e in enumerate(edges):
            e = [args['rooms'][x] for x in e]
            args['doors'][i] = Door.generate(tables, i, e)

        # generate encounters
        args['monsters'] = {}
        encounter_count = math.ceil(room_count * (encounter_room_percent / 100))
        monster_store = MonsterStore(tables)
        base_monster_list = monster_store.filter(environment_filter=args['parameters']['environments'],
                                                 alignment_filter=monster_alignments,
                                                 type_filter=monster_types,
                                                 source_filter=monster_sources)
        all_rooms = [x for x in args['rooms'].keys() if not args['rooms'][x].is_corridor]
        for difficulty in generate_avg_list(encounter_average_difficulty, encounter_count,
                                            MonsterStore.EASY, MonsterStore.DEADLY):
            room_id = random.choice(all_rooms)
            room = args['rooms'][room_id]
            encounter = monster_store.create_encounter(character_levels, difficulty, base_monster_list, room.size_integer)
            if encounter is not None:
                for m in encounter:
                    m.location = room_id
                    args['monsters'][m.id] = m
            all_rooms.remove(room_id)
            if not all_rooms:
                break


        return Dungeon(**args)

        # get the overall dungeon settings
        environments = tables.lookup("settings", "monsters", "environments")

        # distribute the keys in locations where they can be found.
        self.map.hide_door_keys()



        encounter = Encounter(tables, character_levels, source_filter=monster_sources, 
                              type_filter=monster_types, alignment_filter=monster_alignments,
                              environment_filter=environments)
        encounter_count = math.ceil(room_count * (encounter_room_percent / 100))
        difficulties = generate_avg_list(encounter_average_difficulty, encounter_count, Encounter.EASY, Encounter.DEADLY)
        # get all of the rooms (but not corridors or the start room)
        non_monster_rooms = set([x for x in self.map.get_nodes() if x.type == Node.ROOM])
        for d in difficulties:
            e = encounter.create_encounter(d)
            r = random.choice(list(non_monster_rooms))
            for m in e:
                m.set_location(r.id)
                m.decorate(tables)
                self.monsters[m.id] = m
            non_monster_rooms.remove(r)
            print(f"Wanted difficulty {d}, got encounter {e}, placed in room {r.id}")
            
        # generate the wandering mosnters
        difficulties = generate_avg_list(encounter_average_difficulty, wandering_monsters, Encounter.EASY, Encounter.DEADLY)
        for difficulty in difficulties:
            wm = encounter.create_wandering_monster(difficulty)
            wm.set_location(None)
            wm.decorate(tables)
            self.monsters[wm.id] = wm


    def get_monsters_for_room(self, room_id):
        r = []
        for mon in self.monsters.values():
            if mon.is_alive() and mon.get_location() == room_id:
                r.append(mon)
        return r

    def get_wandering_monster(self):
        wms = [m for m in self.monsters.values() if m.is_alive() and m.get_location() is None]
        if wms:
            return random.choice(wms)
        else:
            return None        





