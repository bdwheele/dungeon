from .tables import Tables
from .utils import roll_dice

class Treasure:
    def __init__(self, tables):
        self.tables = tables
        
    def generate_individual(self, cr):
        for low, high in ([0, 4], [5, 10], [11, 16], [17, 100]):
            if low <= cr <= high:
                tabname = f"individual_{low}_{high}"

        result = []
        treasure_list = self.tables.random('treasure', tabname)
        for t in treasure_list:
            result.append(f"{roll_dice(t['count'])} {t['unit']}")
        return result
