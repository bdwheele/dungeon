import math
import random
import subprocess
from pathlib import Path
from .door import Door
from .graph import gen_graph
from .mergeable import Mergeable
from .monster import MonsterStore
from .room import Room
from .utils import gen_id, generate_avg_list, is_template, template, get_template_vars, array_random
from .flags import process_flags

# THE DUNGEON!
# The dungeon serves as a container for everything about the dungeon:  the rooms, doors,
# monsters, treasure, etc.  It also contains the information about the game in progress.
#
class Dungeon(Mergeable):
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
            self.player_data = {}
            self.state = {
                'current_room': 0,
                'current_time': 0
            }
            self.objects = {}
            # and then override whatever we got from the kwargs
            self.merge_attrs(kwargs)
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
        dungeon = Dungeon(version=1)
        dungeon.parameters = tables.get_table('dungeon', 'parameters')
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
        for node_id in node_edges:
            room_id = f"R{node_id}"
            dungeon.objects[room_id] = Room.generate(tables, room_id, len(node_edges[node_id]))

        # create doors/passages from all of the edges
        for i, e in enumerate(edges):
            i = f"D{i}"
            e = [dungeon.objects[f"R{x}"] for x in e]
            dungeon.objects[i] = Door.generate(tables, i, e)

        # put the door objects into the rooms (insetad of just ids).
        for node_id in node_edges:
            room_id = f"R{node_id}"
            doors = [dungeon.objects[f"D{x}"] for x in node_edges[node_id]]
            dungeon.objects[room_id].doors = doors

        # generate encounters
        encounter_count = math.ceil(room_count * (encounter_room_percent / 100))
        monster_store = MonsterStore(tables)
        base_monster_list = monster_store.filter(environment_filter=dungeon.parameters['environments'],
                                                 alignment_filter=monster_alignments,
                                                 type_filter=monster_types,
                                                 source_filter=monster_sources)
        all_rooms = [x for x in dungeon.find_objects(Room) if not x.is_corridor]
        for difficulty in generate_avg_list(encounter_average_difficulty, encounter_count,
                                            MonsterStore.EASY, MonsterStore.DEADLY):
            #room_id = random.choice(all_rooms)
            #room = dungeon.objects[room_id]
            room = random.choice(all_rooms)
            encounter = monster_store.create_encounter(character_levels, difficulty, base_monster_list, room.size_integer)
            if encounter is not None:
                for m in encounter:
                    m.location = room
                    m.decorate()
                    dungeon.objects[m.id] = m
                    room.store(m)
            all_rooms.remove(room)
            if not all_rooms:
                break



        # pick the starting room
        start_room = random.choice([x for x in dungeon.find_objects(Room) if not x.is_corridor])
        start_room.visited = True
        start_room.is_start = True
        dungeon.state['current_room'] = start_room

            
        # generate the wandering monsters
        difficulties = generate_avg_list(encounter_average_difficulty, wandering_monsters, MonsterStore.EASY, MonsterStore.DEADLY)
        for difficulty in difficulties:
            monster = monster_store.create_wandering_monster(character_levels, difficulty, base_monster_list)
            dungeon.objects[monster.id] = monster

        # TODO:  handle flags on EVERYTHING
        todo_objects = list(dungeon.objects.values())
        done_objects = set()
        while todo_objects:
            for o in todo_objects:
                done_objects.add(o)
                process_flags(o, dungeon, tables)

            todo_objects = [x for x in list(dungeon.objects.values()) if x not in done_objects]           


        # TODO:  fill in any templates
        for o in dungeon.objects.values():
            if hasattr(o, 'description'):
                for i, d in enumerate(o.description):
                    if is_template(d):
                        print(f"Object {o.id} has a template in description[{i}], needing keys {get_template_vars(d)}: {d}")
                        vals = {}
                        for v in get_template_vars(d):
                            vals[v] = array_random(tables.get_table('dressing', v))
                        o.description[i] = template(d, vals)
                        print(f"   Result: {o.description[i]}")


        # TODO:  hide keys 

        return dungeon


    def generate_map_dot(self, all_rooms=False):
        dot = ["graph dungeon_map {",
               "  rankdir = LR;"]
        rooms = self.find_objects(Room) if all_rooms else [x for x in self.find_objects(Room) if x.visited]
        print([x.id for x in rooms])
        seen_doors = set()
        for room in rooms:
            shape = 'house'
            if room.is_start:
                shape = 'octagon'
            elif room.is_corridor:
                shape = 'rectangle'

            style = ', style="filled"' if room == self.state['current_room'] else ""
            dot.append(f'{room.id} [label="{room.id}", shape="{shape}", URL="#{room.id}"{style}];')
            for door in room.doors:
                if not door in seen_doors:
                    seen_doors.add(door)
                    if door.visited or all_rooms:
                        a, b = [x.id for x in door.sides]
                    else: # one side is a mystery!
                        a = "x" + str(gen_id('map_room'))
                        dot.append(f'{a} [label="?", shape="circle"];')
                        b = door.sides[0].id if door.sides[0].visited else door.sides[1].id
                    style = 'solid' if door.is_passage else 'dashed'
                    dot.append(f'{a} -- {b} [label="{door.id}", style="{style}"];')
        dot.append("}")
        return "\n".join(dot)


    def find_objects(self, cls):
        """
        Return all of the objects which are instances of
        the class specified in cls
        """
        result = []
        for x in self.objects.values():
            if isinstance(x, cls):
                result.append(x)
        return result

    def add_object(self, thing):
        self.objects[thing.id] = thing

