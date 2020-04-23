from yaml import YAMLObject
from .graph import gen_graph
from .door import Door
from .room import Room


from .map import Map
from .node import Node
from .edge import Edge
from .monster import Encounter, Monster
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
                    setattr(k, kwargs[k])
        else:
            raise ValueError(f"Cannot create dungeon version {version}")

    @staticmethod
    def generate(tables, room_count=10, character_levels=[1, 1, 1, 1],
                 monster_sources=['mm'], monster_types=[], monster_alignments=[],
                 encounter_average_difficulty=Encounter.MEDIUM,
                 encounter_room_percent=25, wandering_monsters=6): 
        """
        Generate a dungeon based on the parameters given, as well as the parameters
        from the settings/parameters table for the current style.
        """
        parameters = tables.get_table('settings', 'parameters')
        edges = gen_graph(room_count, 
                          edge_dist=tables.get_table('graph', 'edges_per_node'),
                          use_existing_node_dist=tables.get_table('graph', 'edge_connect_existing'),
                          edge_distance_dist=tables.get_table('graph', 'edge_distance'))

        # the edges data tells us all of the room ids and how they're
        # connected, but we need to compute the list of edge connections
        # per node to give context to the room generator
        node_ids = {}
        for i, edge in enumerate(edges):
            for con in edge:
                if con not in node_ids:
                    node_ids[con] = []
                else:
                    node_ids[con] += 1
        # generate the rooms
        rooms = {}
        for node_id in node_ids:
            rooms[node_id] = Room(tables, node_id, node_ids[node_id])

        # create doors/passages from all of the edges
        doors = []
        for e in edges:
            pass




        # get the overall dungeon settings
        environments = tables.lookup("settings", "monsters", "environments")

        # generate the map and decorate the rooms
        self.map.generate(tables, room_count)
        for e in self.map.get_edges():
            e.decorate(tables)
        for n in self.map.get_nodes():
            n.decorate(tables)

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





