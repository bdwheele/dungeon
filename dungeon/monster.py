import random
import math
import copy
from .utils import gen_id
from .treasure import Treasure

class Encounter:
    EASY = 0
    MEDIUM = 1
    HARD = 2
    DEADLY = 3

    def __init__(self, tables, character_levels, source_filter=[], 
                 alignment_filter=[], type_filter=[], environment_filter=[]):
        self.tables = tables
        self.character_levels = character_levels
        if not isinstance(character_levels, list) or len(character_levels) < 1:
            raise ValueError("There must be at least one player")
        # load all monsters
        self.monsters = self.tables.find_table('monsters', 'monsters')
        print(f"Monsters loaded: {len(self.monsters)}")

        # filter by source
        if source_filter:
            self.monsters = [x for x in self.monsters if x['source'] in source_filter]
            print(f"Monsters after source filter {source_filter}: {len(self.monsters)}")

        if alignment_filter:
            self.monsters = [x for x in self.monsters if x['alignment'] in alignment_filter]
            print(f"Monsters after alignment filter {alignment_filter}: {len(self.monsters)}")

        if type_filter:
            self.monsters = [x for x in self.monsters if x['type'] in type_filter]
            print(f"Monsters after type fitler {type_filter}: {len(self.monsters)}")

        if environment_filter:
            environment_filter = set(environment_filter)
            self.monsters = [x for x in self.monsters if 'any' in environment_filter or set(x['environment']).intersection(environment_filter)]
            print(f"Monsters after environment filter {environment_filter}: {len(self.monsters)}")

        print(f"Monsters left to choose from: {len(self.monsters)}")


    @staticmethod
    def get_sources(tables):
        return tables.find_table('monsters', 'sources')

    def compute_party_threshold(self, difficulty):
        xp_thresh = 0
        for level in self.character_levels:
            xp_thresh += self.tables.lookup('encounter', 'player_xp_thresholds', level)[difficulty]
        return xp_thresh

    def cr_to_xp(self, cr):
        try:
            return self.tables.lookup('encounter', 'cr_to_xp', cr)
        except KeyError as e:
            print(f"Cannot convert: {e}")
            return 1_000_000_000

    def get_encounter_multiplier(self, party_size, monster_count):
        t = self.tables.find_table('encounter', 'encounter_multipliers')
        for i, v in enumerate(t):
            if v['min'] <= monster_count <= v['max']:
                break
        if party_size < 3:
            i = min(i + 1, len(t))
            if i == len(t):
                return 5
        elif party_size > 5:
            i = max(0, i - 1)
            if i == 0:
                return 0.5
        return t[i]['x']
        

    def create_encounter(self, difficulty):
        # calculate party threshold
        xp_thresh = self.compute_party_threshold(difficulty)

        # filter monsters which are less than the threshold
        monsters = [x for x in self.monsters if self.cr_to_xp(x['cr']) < xp_thresh]
        encounters = []
        for m in monsters:
            xp = self.cr_to_xp(m['cr'])
            base_xp = xp
            count = 1
            while True:
                count += 1
                multiplier = self.get_encounter_multiplier(len(self.character_levels), count)
                proposed_xp = count * base_xp * multiplier
                if proposed_xp > xp_thresh:
                    count -= 1
                    m['xp'] = math.floor(xp / count)
                    break
                xp = proposed_xp

            group = []
            for x in range(count):
                group.append(Monster(m))
            encounters.append(group)

        return random.choice(encounters)

 
    def create_wandering_monster(self, difficulty):
        xp_thresh = self.compute_party_threshold(difficulty)
        # filter monsters which are less than the threshold
        monsters = [x for x in self.monsters if self.cr_to_xp(x['cr']) < xp_thresh]
        return Monster(random.choice(monsters))


def cr_to_decimal(cr):
    return {'1/8': 0.125, '1/4': 0.25, '1/2': 0.5}.get(cr, cr)

class Monster:
    def __init__(self, prototype=None):
        self.id = gen_id('monster')
        self.attributes = {}
        self.state = {}

        if prototype:
            self.state = {
                'alive': True,
                'location': None,
                'property': []
            }
            self.attributes = copy.deepcopy(prototype)

    
    def decorate(self, tables):
        # give the monster appropriate treasure?
        if self.attributes['type'].lower() == 'humanoid':
            # give them some coins, based on cr
            treasure = Treasure(tables)
            x = treasure.generate_individual(cr_to_decimal(self.attributes['cr']))
            self.state['property'].extend(x)


    @staticmethod
    def load(data):
        m = Monster()
        m.state = data['state']
        m.attributes = data['attributes']
        m.id = data['id']
        return m

    def save(self):
        return {
            'id': self.id,
            'state': self.state,
            'attributes': self.attributes
        }

    def get_location(self):
        return self.state['location']

    def set_location(self, node_id):
        self.state['location'] = node_id

    def is_alive(self):
        return self.state['alive']

    def kill(self):
        self.state['alive'] = False

    def get_property(self):
        return self.state['property']

    def get_attributes(self):
        return self.attributes
