from math import floor
from random import randint, choices, choice
import re
from copy import deepcopy

"""
Miscellaneous utility functions that are useful for many things
"""

id_state = {}
def gen_id(table, seed=1, random=False, prefix=None, random_limit=4095):
    """
    Generate a per-program-run-unique ID either by using a 
    random number or by incrementing a counter. optionally,
    a prefix can be added to the ID
    """
    new_id = None
    if random:
        if table not in id_state:
            id_state[table] = set()
        new_id = randint(0, random_limit)
        while new_id in id_state[table]:
            new_id = randint(0, random_limit)
        id_state[table].add(new_id)
    else:
        if table not in id_state:
            id_state[table] = seed
        else:
            id_state[table] += 1
        new_id = id_state[table]
    if prefix is not None:
        new_id = prefix + str(new_id)
    return new_id


def generate_avg_list(average, count, min, max):
    """
    Generate a list of <count> integers between <min> and <max> with 
    an average of <average>.  Average itself need not be an integer.
    """
    avg = max
    sum = 0
    numbers = []
    for n in range(0, count):
        if avg < average:
            n = randint(floor(avg), max)
        else:
            n = randint(min, floor(avg))
        sum += n
        numbers.append(n)
        avg = sum / len(numbers)
    return numbers


def roll_dice(spec):
    """
    Given a D&D roll specification, generate a random number.  The 
    spec should look like:  1d6, 3d4-2, 2d8+1, 3d6+2x100
    """
    spec_re = re.compile(r"^(\d+)d(\d+)([\+\-]\d+)?(x(\d+))?$")
    spec = spec.replace(' ', '').lower()
    m = spec_re.match(spec)
    if not m:
        raise ValueError(f"Roll spec '{spec}' doesn't seem valid")
    count = int(m.group(1))
    die = int(m.group(2))
    modifier = int(m.group(3) if m.group(3) else 0)
    multiplier = int(m.group(5) if m.group(5) else 1)
    sum = 0
    for _ in range(count):
        sum += randint(1, die)
    return (sum + modifier) * multiplier


def array_random(array):
    """
    Select a random item from an array, based on the structure
    of the array.

    If the array elements are lists, sets, or tuples, then the first item of 
    the element is the relative weight of that element, and the second item 
    of the element is the data that will be returned if that element is chosen.

    If the array elements are anything else, it's assumed to be an even 
    distribution and the elements are the data that will be returned when
    chosen.
    """
    if not array:
        return None

    if isinstance(array[0], (list, set, tuple)):
        weights, values = list(zip(*array))
        return deepcopy(choices(values, weights=weights, k=1)[0])
    else:
        return deepcopy(choice(array))

def template(string, values):
    for k, v in values:
        string = string.replace(f"{k}", v)
    return string