from collections import namedtuple
import re
from .utils import roll_dice, array_random, gen_id
import math
from .door import Door
from .trappable import Trappable
from .lockable import Lockable
from .container import Container
from .thing import Thing

#
# Flags
#

def parse_flag(flag):
    """
    convert a flag specification into its component parts.  A
    flag has this format: (repeats)flag[args]  where the
    (repeats) and [args] are optional.  The [args] are a list of
    key=value pairs, separated by commas.  The (repeats) is either
    an integer or a roll specification.
    examples:
        FLAG  - a single flag with no arguments
        (3)FLAG - flag will get repeated 3 times
        (3d6-1)FLAG - flag will get repeated 0 to 17 times
        FLAG[arg1=value] - a single flag with arg1 set to value
        (3)FLAG[arg1=value; arg2=value] - 3 flags with args
    """
    Flag = namedtuple('Flag', ['name', 'repeat', 'args'])
    fmt = re.compile(r"^(\((.+?)\))?([^\[]+?)(\[(.+?)\])?$")
    m = fmt.match(flag)
    if not m:
        raise ValueError(f"'{flag}' doesn't seem like a valid flag specification")
    repeat = m.group(2)
    name = m.group(3)
    args = m.group(5)
    if repeat:
        if re.match(r"^\d+$", repeat):
            repeat = int(repeat)
        else:
            repeat = roll_dice(repeat)
    else:
        repeat = 1

    argdata = {}    
    if args:
        for pair in args.split(';'):
            if '=' not in pair:
                raise ValueError("Flag arguments must be key=value pairs")
            k, v = pair.split('=', maxsplit=1)
            argdata[k.strip()] = v.strip()

    return Flag(name.upper(), repeat, argdata)
    

def process_flags(obj, dungeon, tables):
    """
    This walks through an object's flags and processes them in the context
    of the dungeon.  Creating locks & keys, traps, treasure, etc.
    """
    flags_todo = list(obj.flags)
    while flags_todo:
        flag = parse_flag(flags_todo.pop(0))
        for _ in range(flag.repeat):
            if flag.name == 'TRAP':
                # generate a trap
                pass
            elif flag.name == 'LOCKED':
                # generate a lock & key
                if isinstance(obj, Lockable):
                    # create the lock
                    obj.has_lock = True
                    obj.is_locked = True
                    obj.lock_pick_dc = math.floor(obj.break_down_dc * 0.75)
                    # create the key object
                    key = Thing()
                    key.id = gen_id('key', prefix='K')
                    key.location = None
                    code = gen_id('key_code', random=True, reserved=[666])
                    key.description = ["{key_size} key made of {key_material}", f"Key code: {key.id}"]
                    obj.lock_code = code
                    dungeon.add_object(key)
            elif flag.name == 'STUCK':
                # for doors, the door is stuck
                if isinstance(obj, Door):
                    obj.is_stuck = True
                    obj.stuck_dc = math.floor(obj.break_down_dc / 2)
            elif flag.name == 'TREASURE':
                # generate some treasure for this object
                print(f"Treasure: {flag}")


                pass
            elif flag.name == 'OBJECT':
                print(f"Generic object {flag}")
                new_obj = Thing()
                if 'description' not in flag.args:
                    raise ValueError("Can't create an object without a description!")
                new_obj.description = [flag.args['description']]
                new_obj.id = gen_id('object', prefix='O')
                new_obj.location = obj
                if 'flags' in flag.args:
                    new_obj.flags = flag.args.split(',')
                obj.store(new_obj)
                dungeon.add_object(new_obj)



            else:
                # don't know how to handle this...
                print(f"Don't know how to handle flag {flag.name} for {obj}")

