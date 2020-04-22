# Nodes (rooms/corridors) 
import logging
import copy
from .utils import mergedata, gen_id

logger = logging.getLogger()

class Node:
    UNTYPED = 0
    START = 1
    ROOM = 2
    CORRIDOR = 3

    def __init__(self, t, depth=0, exit_goal=0):
        self.type = t
        self.id = gen_id('node')
        self.exits = []
        self.exit_goal = exit_goal
        self.depth = depth
        self.attributes = {}
        # this is a placeholder used during construction when
        # hiding keys.
        self.temp_keys = set()

    @staticmethod
    def load(data):
        "restore a node from a dict"
        n = Node(data['type'], data['depth'], data['exit_goal'])
        n.id = data['id']
        n.attributes = data['attributes']
        n.exits = data['exits']
        return n

    def save(self):
        "dump the node as a dict"
        return {
            'type': self.type,
            'id': self.id,
            'exits': self.exits,
            'depth': self.depth,
            'exit_goal': self.exit_goal,        
            'attributes': self.attributes
        }


    def add_exit(self, edge):
        self.exits.append(edge)

    def can_add_exit(self):
        return len(self.exits) < 4
            
    def may_add_exit(self):
        return len(self.exits) < self.exit_goal

    def exit_count(self):
        return len(self.exits)

    ### Decoration
    def decorate(self, tables):
        # structure the node attributes
        self.attributes = {
            'description': [],
            'flags': [],
            'traps': [],
            'state': {
                'visited': self.type == Node.START,
                'contents': [],
                'features': [],
            },
        }


        if self.type == Node.START or self.type == Node.ROOM:
            room = tables.random('decorate_room', 'kind')
            shape = tables.random('decorate_room', 'shape')
            exits = self.exit_count()
            size = tables.random('decorate_room', f'size_{exits}')
            room['description'].append(f"The room is {size} and {shape}-shaped")
            
            state = tables.random('decorate_room', 'state')
            room['description'].append(state['state'])
            if 'WATER' in state['flags']:
                room['description'].append(tables.random('decorate_room', 'water')['description'])
            mergedata(self.attributes, room)

        elif self.type == Node.CORRIDOR:
            exits = self.exit_count()
            if exits == 1:
                mergedata(self.attributes, tables.random("decorate_corridor", "corridor_ends"))
            elif exits == 2:
                mergedata(self.attributes, tables.random("decorate_corridor", "corridor_through"))
            else:
                mergedata(self.attributes, {'description': [f"The corridor branches into {exits} routes, including the one you came from"]})

        # TODO: Handle flags

    def visit(self):
        self.attributes['state']['visited'] = True

    def hide_key(self, key):
        # for now, just put it into the contents list
        self.attributes['state']['contents'].append(key[1])
        self.temp_keys.add(key[0])

    def get_keys(self):
        # get a list of the key ids which are in this room.
        return self.temp_keys


    def add_content(self, content):
        self.attributes['state']['contents'].append(content)

    def remove_content(self, content):
        self.attributes['state']['contents'].remove(content)

    def add_feature(self, content):
        self.attributes['state']['features'].append(content)

    def remove_feature(self, content):
        self.attributes['state']['features'].remove(content)

