import math
import random
import subprocess
from pathlib import Path
from .door import Door
from .graph import gen_graph
from .mergeable import Mergeable
from .monster import MonsterStore
from .room import Room
from .utils import gen_id, generate_avg_list, is_template, template, get_template_vars, array_random, roll_dice
from .flags import process_flags
from .key import Key

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
                'current_room': None,
                'current_time': 0
            }
            self.objects = {}
            self.start_room = None
            # and then override whatever we got from the kwargs
            self.merge_attrs(kwargs)
        else:
            raise ValueError(f"Cannot create dungeon version {version}")


    def find_objects(self, *classes):
        """
        Return all of the objects which are instances of
        the class specified in cls
        """
        return [x for x in self.objects.values() if x.is_a(*classes)]

    def add_object(self, thing):
        self.objects[thing.id] = thing
        return thing


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

        # the edges data tell us how things are connected, but we don't have 
        # any objects yet.  Doors and Rooms are co-dependent so they're
        # a little tricky.
        rooms = {}
        doors = {}
        for i, edge in enumerate(edges):
            doors[i] = dungeon.add_object(Door())
            for s in edge:
                if s not in rooms:
                    rooms[s] = dungeon.add_object(Room())
                rooms[s].store(doors[i])
                doors[i].sides.append(rooms[s])

        # Decorate the newly-minted rooms and doors
        for r in rooms.values():
            r.decorate(tables)
        for d in doors.values():
            d.decorate(tables)

        # generate encounters
        encounter_count = math.ceil(room_count * (encounter_room_percent / 100))
        monster_store = MonsterStore(tables)
        base_monster_list = monster_store.filter(environment_filter=dungeon.parameters['environments'],
                                                 alignment_filter=monster_alignments,
                                                 type_filter=monster_types,
                                                 source_filter=monster_sources)
        all_rooms = [x for x in dungeon.find_objects("Room") if not x.is_corridor]
        for difficulty in generate_avg_list(encounter_average_difficulty, encounter_count,
                                            MonsterStore.EASY, MonsterStore.DEADLY):
            room = random.choice(all_rooms)
            encounter = monster_store.create_encounter(character_levels, difficulty, base_monster_list, room.size_integer)
            if encounter is not None:
                for m in encounter:
                    m.decorate(tables)
                    dungeon.add_object(m)
                    room.store(m)
            all_rooms.remove(room)
            if not all_rooms:
                break


        # pick the starting room
        start_room = random.choice([x for x in dungeon.find_objects(Room) if not x.is_corridor])
        start_room.visited = True
        dungeon.start_room = start_room
        dungeon.state['current_room'] = start_room

            
        # generate the wandering monsters
        difficulties = generate_avg_list(encounter_average_difficulty, wandering_monsters, MonsterStore.EASY, MonsterStore.DEADLY)
        for difficulty in difficulties:
            monster = dungeon.add_object(monster_store.create_wandering_monster(character_levels, difficulty, base_monster_list))
            monster.decorate()

        # Handle flags on everything
        todo_objects = list(dungeon.objects.values())
        done_objects = set()
        while todo_objects:
            for o in todo_objects:
                done_objects.add(o)
                process_flags(o, dungeon, tables)

            todo_objects = [x for x in list(dungeon.objects.values()) if x not in done_objects]           


        # Fill in any templates
        for o in dungeon.objects.values():
            if hasattr(o, 'description'):
                for i, d in enumerate(o.description):
                    if is_template(d):
                        vals = {}
                        for v in get_template_vars(d):
                            if '.' in v:
                                group, table = v.split('.', 1)
                            else:
                                group = 'dressing'
                                table = v
                            vals[v] = array_random(tables.get_table(group, table))
                        o.description[i] = template(d, vals)

        #dungeon.hide_keys()
        return dungeon



    def hide_keys(self):
        """
        This is a lot harder now that we have more than just doors that can be
        locked.  The theory is the same as the old implementation:  from the
        starting room walk each locked item in the room 
        """
        # find all of the keys to hide
        keys_to_hide = set([x for x in self.find_objects('Key') if x.location is None])
        
        room_count = 0
        for o in self.objects.values():
            if isinstance(o, Key) and o.location is None:
                keys_to_hide.add(o)
            if isinstance(o, Room):
                room_count += 1
                if o.is_start:
                    start_room = o
        print(f"{len(keys)} to hide, {len(rooms)} rooms in dungeon.")
        while True:
            visited_rooms = set()
            keychain = set()
            todo = set([start_room])
            needed_keys = set()
            while todo:
                here = todo.pop(0)
                visited_rooms.add(here)
                for x in here.get_recursive_contents():
                    if isinstance(x, Key):
                        keychain.add(x)
                for door in here.doors:
                    if not door.has_lock:
                        # go through.
                        todo.append([x for x in door.sides if x not in visited_rooms])
                    else:
                        if door.lock_key in keychain:
                            # we can unlock this with the keys we know.
                            todo.append([x for x in door.sides if x not in visited_rooms])
                        else:
                            if door.lock_key not in keys_to_hide:
                                pass

            if len(visited_rooms) == len(rooms):
                break



    def generate_map_dot(self, all_rooms=False):
        dot = ["graph dungeon_map {",
               "  rankdir = LR;"]
        rooms = self.find_objects(Room) if all_rooms else [x for x in self.find_objects(Room) if x.visited]
        seen_doors = set()
        for room in rooms:
            shape = 'house'
            if room == self.start_room:
                shape = 'octagon'
            elif room.is_corridor:
                shape = 'rectangle'

            style = ', style="filled"' if room == self.state['current_room'] else ""
            dot.append(f'{room.id} [label="{room.id}", shape="{shape}", URL="#{room.id}"{style}];')
            for door in [x for x in room.contents if x.is_a("Door")]:
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

