from collections import namedtuple
import re
from .utils import roll_dice, array_random, gen_id
import math
from random import randint
from .door import Door
from .trappable import Trappable
from .lockable import Lockable
from .container import Container
from .thing import Thing
from .monster import MonsterStore
from .treasure import Treasure
from .key import Key

#
# Flags
#
def parse_flag(flag):
    """
    Convert a flag specification into its component parts.  

    Flags come in two flavors:  a simple string or a complex dict.

    A simple string is turned into a name, with the rest of the fields default

    The complex dict should contain exactly 1 key:  the flag name.  The
    values of that key become the args for the flag.  If percent and count are
    specified, they are removed and placed into the flag itself.

    """
    Flag = namedtuple("Flag", ('name', 'percent', 'count', 'args'))

    if isinstance(flag, str):
        return Flag(flag, 100, 1, {})
    if not isinstance(flag, dict):
        raise ValueError(f"Cannot process non-dictionary {flag} as flag.")
    if len(flag.keys()) != 1:
        raise ValueError(f"Flag dictionaries can only contain one key: {flag}")

    name = list(flag.keys())[0]
    args = flag[name]
    percent = args.get('percent', 100)
    count = args.get('count', 1)
    if re.match(r"^\d+$", str(count)):
        count = int(count)
    else:
        count = roll_dice(count)
    if 'description' in args:
        if isinstance(args['description'], str):
            args['description'] = [args['description']]

    return Flag(name.upper(), percent, count, args)



def process_flags(obj, dungeon, monster_store, tables):
    """
    This walks through an object's flags and processes them in the context
    of the dungeon.  Creating locks & keys, traps, treasure, etc.
    """
    treasure = Treasure(tables)
    new_objects = []
    for raw_flag in obj.flags:
        #print(f"RAW_FLAG: {raw_flag}")
        flag = parse_flag(raw_flag)
        pct = randint(1, 100)
        #print(f"FLAG: {flag.name}, {flag.percent}/{pct}, {flag.count}, {flag.args}")
        if pct > flag.percent:
            #print("*** SKIPPING ***")
            # it's not here
            continue

        for _ in range(flag.count):
            if flag.name == 'TRAP':
                # generate a trap
                pass
            elif flag.name == 'LOCKED':
                # generate a lock & key
                #print(f"Adding lock to {obj.id}")
                if obj.is_a("Lockable"):
                    # create the lock
                    obj.has_lock = True
                    obj.is_locked = True
                    obj.lock_pick_dc = math.floor(obj.break_dc * 0.75)
                    # create the key object
                    key = Key()
                    new_objects.append(key)
                    key.location = None                    
                    obj.lock_key = key
            elif flag.name == 'STUCK':
                # for doors, the door is stuck
                if obj.is_a("Door"):
                    obj.is_stuck = True
                    obj.stuck_dc = math.floor(obj.break_dc / 3)
            elif flag.name == 'TREASURE':
                # generate some treasure for this object
                new_obj = Thing()
                new_objects.append(new_obj)
                new_obj.description = treasure.generate(treasure_type=flag.args['type'], cr=flag.args['cr'])
                obj.store(new_obj)

            elif flag.name == 'OBJECT':
                # create a new object by hand
                new_obj = Thing()
                new_objects.append(new_obj)
                new_obj.merge_attrs(flag.args)
                if 'description' not in flag.args:
                    raise ValueError("Can't create an object without a description!")
                obj.store(new_obj)

            elif flag.name == "CATALOG":
                # pull an item out of the catalog and possibly update it with
                # local values 
                group = 'catalog'
                if '.' in flag.args['name']:
                    group, name = flag.args['name'].split('.', 1)
                else:
                    name = flag.args['name']
                new_obj = Thing()
                new_obj.merge_attrs(tables.get_table(group, name))
                print(new_obj)
                new_objects.append(new_obj)
                obj.store(new_obj)

            elif flag.name == 'MONSTER':
                monster = monster_store.get_monster(flag.args['name'])
                monster.decorate(tables)
                new_objects.append(monster)
                obj.store(monster)        
            else:
                # don't know how to handle this...
                print(f"Don't know how to handle flag {flag.name} for {obj}")

    return new_objects