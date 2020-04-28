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
    percent = args.pop('percent') if 'percent' in args else 100
    count = args.pop('count') if 'count' in args else 1
    if re.match(r"^\d+$", str(count)):
        count = int(count)
    else:
        count = roll_dice(count)
    if 'description' in args:
        if isinstance(args['description'], str):
            args['description'] = [args['description']]

    return Flag(name.upper(), percent, count, args)



def process_flags(obj, dungeon, tables):
    """
    This walks through an object's flags and processes them in the context
    of the dungeon.  Creating locks & keys, traps, treasure, etc.
    """
    flags_todo = list(obj.flags)
    monster_store = MonsterStore(tables)
    treasure = Treasure(tables)
    while flags_todo:
        flag = parse_flag(flags_todo.pop(0))
        if randint(1, 100) > flag.percent:
            # it's not here
            continue

        for _ in range(flag.count):
            print(f"FLAG:  {flag.name}, args: {flag.args}")
            if flag.name == 'TRAP':
                # generate a trap
                pass
            elif flag.name == 'LOCKED':
                # generate a lock & key
                print(f"Adding lock to {obj.id}")
                if obj.is_a("Lockable"):
                    # create the lock
                    obj.has_lock = True
                    obj.is_locked = True
                    obj.lock_pick_dc = math.floor(obj.break_dc * 0.75)
                    # create the key object
                    key = dungeon.add_object(Key())
                    key.location = None                    
                    obj.lock_key = key
            elif flag.name == 'STUCK':
                # for doors, the door is stuck
                if obj.is_a("Door"):
                    obj.is_stuck = True
                    obj.stuck_dc = math.floor(obj.break_dc / 3)
            elif flag.name == 'TREASURE':
                # generate some treasure for this object
                new_obj = dungeon.add_object(Thing())
                new_obj.description = treasure.generate(treasure_type=flag.args['type'], cr=flag.args['cr'])
                obj.store(new_obj)

            elif flag.name == 'OBJECT':
                new_obj = dungeon.add_object(Thing())
                new_obj.merge_attrs(flag.args)
                if 'description' not in flag.args:
                    raise ValueError("Can't create an object without a description!")
                obj.store(new_obj)

            elif flag.name == 'MONSTER':
                monster = monster_store.get_monster(flag.args['name'])
                monster.decorate(tables)
                dungeon.add_object(monster)
                obj.store(monster)        
            else:
                # don't know how to handle this...
                print(f"Don't know how to handle flag {flag.name} for {obj}")

