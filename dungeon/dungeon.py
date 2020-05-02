import math
import random
import subprocess
from pathlib import Path
from .door import Door
from .graph import gen_graph
from .mergeable import Mergeable
from .monster import MonsterStore
from .wandering_monsters import WanderingMonsters
from .inventory import Inventory
from .room import Room
from .utils import gen_id, generate_avg_list, is_template, template, get_template_vars, array_random, roll_dice
from .flags import process_flags
import random

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
        wm = dungeon.add_object(WanderingMonsters())
        difficulties = generate_avg_list(encounter_average_difficulty, wandering_monsters, MonsterStore.EASY, MonsterStore.DEADLY)
        for difficulty in difficulties:
            monster = dungeon.add_object(monster_store.create_wandering_monster(character_levels, difficulty, base_monster_list))
            wm.store(monster)
            monster.decorate(tables)

        # Handle flags on everything
        todo = list(dungeon.objects.values())
        while todo:
            obj = todo.pop()
            new = process_flags(obj, dungeon, monster_store, tables)
            for o in new:
                dungeon.add_object(o)
            todo.extend(new)

        # Fill in any templates
        for o in dungeon.objects.values():
            if hasattr(o, 'description'):
                for i, d in enumerate(o.description):
                    while is_template(d): 
                        vals = {}
                        for v in get_template_vars(d):
                            if v.startswith("roll:"):
                                vals[v] = roll_dice(v[5:])
                            else:
                                if '.' in v:
                                    group, table = v.split('.', 1)
                                else:
                                    group = 'dressing'
                                    table = v
                                vals[v] = array_random(tables.get_table(group, table))
                        d = template(d, vals)
                    o.description[i] = d

        dungeon.hide_keys()

        # put the dungeon on a diet:  there are lots of things which are needed
        # for generation that are never needed again.  clear them out!
        for o in dungeon.objects.values():
            # part 1: convert flags into a set of keys, rather than
            # the full details.
            flags = set()
            for f in o.flags:
                if isinstance(f, str):
                    flags.add(f)
                else:
                    flags.add(list(f.keys())[0])
            o.flags = list(flags)
            # part 2: remove monster environments
            #if o.is_a('Monster'):
            #    del o.environment

        # Create the players' inventory
        dungeon.add_object(Inventory())
    
        return dungeon



    def hide_keys(self):
        """
        This is a lot harder now that we have more than just doors that can be
        locked.  The theory is the same as the old implementation:  from the
        starting room walk each locked item in the room 
        """
        # find all of the keys to hide
        keys_to_hide = set([x for x in self.find_objects('Key') if x.location is None])
        # walk the dungeon, noting all of the needed keys we've 
        # encountered.   All of the container objects found
        # during the walk are possible hiding places.  Hide a
        # single key and walk it again.  Continue doing this
        # until there are no more keys to hide.
        keyring = set()
        while keys_to_hide:
            hiding_places = set()
            todo = set([self.start_room])
            new_keys = set()
            while todo:
                here = todo.pop()
                hiding_places.add(here)
                # find any keys here.
                for k in [k for k in here.contents if k.is_a('Key')]:
                    keyring.add(k)

                # find containers and doors here...
                for c in [c for c in here.contents if c.is_a('Container', 'Door')]:
                    if c.is_a('Lockable'):
                        if not c.has_lock or c.lock_key in keyring:
                            if c.is_a('Door'):
                                other = c.other_side(here)
                                if other not in hiding_places:
                                    todo.add(other)
                            else:
                                if c.can_contain:
                                    todo.add(c)
                        else:
                            if c.lock_key not in keys_to_hide:
                                print(f"{c} needs a key {c.lock_key} that isn't on our to-hide list {keys_to_hide}")
                            else:
                                new_keys.add(c.lock_key)
                    else:
                        if c.can_contain:
                            todo.add(c)                    
                    
            # now we have a set of hiding places and a set of keys we need.
            # pick a random key, and place it into a random hiding place.
            key_to_hide = random.sample(new_keys, 1)[0]  
            hiding_place = random.sample(hiding_places, 1)[0] 
            hiding_place.store(key_to_hide)
            keys_to_hide.remove(key_to_hide)
            keyring.add(key_to_hide)




    def generate_map_dot(self, all_rooms=False):
        dot = ["graph dungeon_map {",
               '  node [fontname="Helvetica", fontsize=8, margin=0, height=0.25, width=0.5];',
               '  edge [fontname="Helvetica", fontsize=8];',
               '  graph [fontname="Helvetica", fontsize=8, overlap=false, splines=true];',
               "  "]
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
                    dot.append(f'{door.id} [label="{door.id}", shape="plain"]')
                    dot.append(f'{a} -- {door.id} -- {b};')
        dot.append("}")
        return "\n".join(dot)


    def generate_object_graph_dot(self):
        """
        Generate a tree of the objects in the dungeon
        """
        result = ["graph {", 
               '  node [fontname="Helvetica", fontsize=8, margin=0, height=0.25, width=0.5];',
               '  edge [fontname="Helvetica", fontsize=8];',
               '  graph [fontname="Helvetica", fontsize=8, overlap=false, splines=true];',
                  ]

        # provide a container for things which don't have a location
        result.append('Unparented [label="Unparented\\nThings", shape="rectangle"];')


        for o in self.objects.values():
            if o.is_a('Container'):
                if o.location is None and not o.is_a('Room'):
                    result.append(f"{o.id} -- Unparented")
                label = f"{o.class_label()} {o.id}\\n{o.description[0][:20]}".replace('"', '\\"')
                style = ', style="filled"' if self.start_room == o else ""
                result.append(f'{o.id} [label="{label}", shape="rectangle"{style}];')
                for c in o.contents:
                    result.append(f'{o.id} -- {c.id};')
            elif o.is_a('Door'):
                # door gets a box with info, and links to the rooms.
                style = 'dashed' if o.is_locked else 'solid'
                result.append(f'{o.id} [label="{o.id}", shape="rectangle", style="{style}", width=0, height=0];')
                if o.is_locked:
                    result.append(f'{o.id} -- {o.lock_key.id} [style="dashed"];')
            elif o.is_a('Key'):
                result.append(f'{o.id} [label="Key\\n{o.id}", shape="rectangle", style="dashed"];')
            else:
                print(f"Don't know how to handle {o}")
        result.append("}")
        return "\n".join(result)