from .tables import Tables
from .utils import roll_dice, array_random

class Treasure:
    def __init__(self, tables):
        self.tables = tables

    def get_range(self, cr):
        for low, high in ([0, 4], [5, 10], [11, 16], [17, 100]):
            if low <= cr <= high:
                return f"{low}_{high}"
        return ""

    def generate(self, treasure_type='i', cr=0):
        tabname = {'i': 'individual', 'h': 'hoard'}.get(treasure_type, 'individual') + "_" + self.get_range(cr)
        description = []
        for t in array_random(self.tables.get_table('treasure', tabname)):
            count = roll_dice(t['count'])
            if 'unit' in t:
                description.append(f"{count}{t['unit']}")
            elif 'table' in t:
                x = array_random(self.tables.get_table('treasure', t['table']))
                description.append(f"{count}x {x}")
            else:
                raise ValueError(f"Can't generate treasure without unit or table: {t}")
        print(description)
        return description
