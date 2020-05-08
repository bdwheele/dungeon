import random
import math
from .utils import gen_id, roll_dice
from .container import Container
from .treasure import Treasure
from .dobject import DObject
from .thing import Thing

class MonsterStore:
    """
    This is where we keep all of the monsters.
    """
    EASY = 0
    MEDIUM = 1
    HARD = 2
    DEADLY = 3


    def __init__(self, tables):
        # get the cr_to_xp table
        self.cr_to_xp_table = tables.get_table('monster', 'cr_to_xp')
        # get the party threshhold table
        self.player_xp_threshold = tables.get_table('monster', 'player_xp_thresholds')
        # get the encounter multiplier table
        self.encounter_multiplier = tables.get_table('monster', 'encounter_multipliers')
        # get the monster size to integer table
        self.size_to_integer_table = tables.get_table('monster', 'size_to_integer')

        # get the monsters
        self.store = []
        for mdata in tables.get_table("monsters", "monsters"):
            mdata['xp'] = self.cr_to_xp(mdata['cr'])
            mdata['decimal_cr'] = self.cr_to_decimal(mdata['cr'])
            mdata['size_integer'] = self.size_to_integer(mdata['size'])
            # convert 'name' into a 1-line description.
            if 'name' in mdata.keys():
                mdata['description'] = [mdata.pop('name')]
            self.store.append(Monster(**mdata))

    def cr_to_decimal(self, cr):
        "convert a challenge rating to decimal for comparisons"
        table = {'1/8': 0.125, 
                 '1/4': 0.25, 
                 '1/2': 0.5}
        if cr not in table:
            return int(cr)
        else:
            return table[cr]

    def cr_to_xp(self, cr):
        "convert a challenge rating to experience points"
        return self.cr_to_xp_table.get(cr, 1_000_000_000)

    def size_to_integer(self, size):
        return self.size_to_integer_table.get(size, 10)

    def compute_party_threshold(self, party, difficulty):
        "compute the xp for a party"
        xp_thresh = 0
        for level in party:
            xp_thresh += self.player_xp_threshold[level][difficulty]
        return xp_thresh

    def get_encounter_multiplier(self, party_size, monster_count):
        "compute the multiplier for an encounter per the mounster count and # of players"
        for i, v in enumerate(self.encounter_multiplier):
            if v[0] <= monster_count <= v[1]:
                break
        if party_size < 3:
            # small parties move down a row (harder)
            i = min(i + 1, len(self.encounter_multiplier))
            if i == len(self.encounter_multiplier): return 5
        elif party_size > 5:
            i = max(0, i - 1)
            if i == 0: return 0.5
        return self.encounter_multiplier[i][2]

    def get_sources(self):
        "Get the valid sources"
        return list(set([x.source for x in self.store])) 
        
    def get_environments(self):
        "Get the valid environments"
        env = []
        for envs in [x.environment for x in self.store]:
            env.extend(*envs)
        return list(set(env))
 
    def get_types(self):
        "Get the valid types"
        return list(set([x.type for x in self.store]))

    def get_alignments(self):
        "Get the valid alignments"
        return list(set([x.alignment for x in self.store]))

    def get_sizes(self):
        "Get the valid monster sizes"
        return list(set([x.size for x in self.store]))


    def get_monster(self, name):
        for m in self.store:
            if m.description[0].lower() == name.lower():
                return m.clone()
        raise ValueError(f"Unknown monster {name} requested")

    def filter(self, monsters=None, source_filter=[], alignment_filter=[], type_filter=[], 
               environment_filter=[], flags_filter=[], size_filter=[],
               min_cr=None, max_cr=None, min_xp=None, max_xp=None):
        "Filter monster list based on some criteria"
        all_monsters = self.store if monsters is None else monsters
        if source_filter:
            all_monsters = [x for x in all_monsters if x.source in source_filter]
        if alignment_filter:
            all_monsters = [x for x in all_monsters if x.alignment in alignment_filter]
        if type_filter:
            all_monsters = [x for x in all_monsters if x.type in type_filter]
        if environment_filter:
            environment_filter = set(environment_filter)
            all_monsters = [x for x in all_monsters if 'any' in environment_filter or set(x.environment).intersection(environment_filter)]
        if flags_filter:
            flags_filter = set(environment_filter)
            all_monsters = [x for x in all_monsters if set(x.flags).intersection(flags_filter)]
        if size_filter:
            all_monsters = [x for x in all_monsters if x.size in size_filter]
        if min_cr or max_cr:
            min_cr = 0 if min_cr is None else self.cr_to_decimal(min_cr)
            max_cr = 100 if max_cr is None else self.cr_to_decimal(max_cr)
            all_monsters = [x for x in all_monsters if min_cr <= x.cr_decimal <= max_cr]
        if min_xp or max_xp:
            min_xp = 0 if min_xp is None else max_xp
            max_xp = 999_999 if max_xp is None else max_xp
            all_monsters = [x for x in all_monsters if min_xp <= self.cr_to_xp(x.cr) <= max_xp]
        return all_monsters

    def create_encounter(self, party, difficulty, monsters, room_size=24):
        """
        This will create a group of monsters from the given monsters
        which (should) be appropriate for the party with given difficulty
        """
        # TODO: Allow mix-and-match monsters.
        # calculate party threshold
        xp_thresh = self.compute_party_threshold(party, difficulty)
        # decrease the room size by the number of medium people in the party
        room_size -= self.size_to_integer('medium') * len(party)
        if room_size < 0:
            # room is too small for the number of people.
            return None
        # remove monsters which are individually too hard
        monsters = self.filter(monsters, max_xp=xp_thresh)
        encounters = []
        for m in monsters:
            xp = self.cr_to_xp(m.cr)
            base_xp = xp
            count = 1
            while m.size_integer * count < room_size:
                count += 1
                multiplier = self.get_encounter_multiplier(len(party), count)
                proposed_xp = count * base_xp * multiplier
                if proposed_xp > xp_thresh:
                    count -= 1
                    break
                xp = proposed_xp

            group = []
            for _ in range(count):
                group.append(m)
            encounters.append(group)
        if not encounters:
            return None
        group = []
        for m in random.choice(encounters):
            # clone the monsters, so we don't corrupt the catalog when dressing them up.
            group.append(m.clone())
    

        return group

    def create_wandering_monster(self, party, difficulty, monsters):
        xp_thresh = self.compute_party_threshold(party, difficulty)
        monsters = self.filter(monsters, max_xp=xp_thresh)
        return random.choice(monsters).clone()


class Monster(DObject, Container):
    """
    A monster.   Behind you.  NO, I'm serious.
    """
    def __init__(self, **kwargs):
        DObject.__init__(self)
        self.is_alive = True
        #self.location = None
        # stuff from the tables...
        self.alignment = None
        self.cr = None
        self.decimal_cr = None
        self.environment = []
        #self.name = "Unnamed Monster"
        self.page = 0
        self.size = None
        self.size_integer = 0
        self.source = None
        self.type = None
        Container.__init__(self)

        self.merge_attrs(kwargs)

    def __str__(self):
        return f"Monster(name={self.description[0]}, type={self.type}, source={self.source}/{self.page}, cr={self.cr}, env={self.environment})"
    
    def decorate(self, tables):
        "Make the monster more than just the catalog entry"
        # Humanoid monsters will have treasure they carry around...
        if self.type.lower() == 'humanoid':
            self.flags.append({'TREASURE': {'type': 'i', 'cr': self.decimal_cr}})
            self.can_contain = True
        else:
            # these monsters don't have a place for stuff.
            self.can_contain = False


    def flee(self):
        "Monster flees!"
        distance = roll_dice('1d6')
        here = self.location
        seen = set()
        exit_door = None
        while distance:
            # get possible doors...
            doors = [x for x in here.contents if x not in seen and x.is_a('Door') and x.is_open]
            if not doors:
                break
            next_door = random.choice(doors)
            if not exit_door:
                exit_door = next_door
            new_room = next_door.other_side(here)
            seen.add(next_door)
            here = new_room
            distance -= 1
        # this is weird, but remember:  the monster is moving itself
        # from its location to another room...
        self.location.transfer(self, here)            
        return exit_door

    def kill(self, dungeon):
        "Dead monsters tell no tales."
        if not self.is_alive:
            return
        # create a corpse object.
        corpse = dungeon.add_object(Thing())
        corpse.is_breakable = False
        corpse.can_contain = True
        corpse.description = [f'The corpse of {self.description[0]} ({self.id})']
        corpse.is_portable = self.size in ('tiny', 'small', 'medium')
        for c in list(self.contents):
            self.transfer(c, corpse)
        self.location.store(corpse)
        self.location.discard(self)



