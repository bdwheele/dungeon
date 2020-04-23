from yaml import YAMLObject
from .utils import gen_id, array_random, template
import logging

logger = logging.getLogger()

class Room(YAMLObject):
    def __init__(self, **kwargs):
        # general room/corridor stuff
        self.id = None
        self.is_start = False
        self.doors = []
        self.is_corridor = False
        self.flags = []
        self.description = []
        self.visited = False
        self.size = 'undetermined'
        # traps
        self.traps = []
        self.traps_found = []
        # contents
        self.contents = []
        self.features = []

        for k in kwargs:
            if hasattr(self, k):
                setattr(self, k, kwargs[k])


    @staticmethod
    def generate(tables, id, doors):
        # build arguments and create the room.
        args = {
            'id': id,
            'doors': doors,
        }

        # determine if this is a room or a corridor
        
        args['is_corridor'] = 'corridor' == array_random(tables.get_table('room', 'room_type'))
        if args['is_corridor']:
            if len(doors) == 1:
                args.update(array_random(tables.get_table('room', 'corridor_ends')))
            elif len(doors) == 2:
                args.update(array_random(tables.get_table('room', 'corridor_through')))
            else:
                args['description'] = [f"The corridor branches into {len(doors)} routes, including the one you came from"]
        else:
            # get the room kind.  This may carry along other attributes
            args.update(array_random(tables.get_table('room', 'room_kind')))
    
            # fill in any details that didn't come from the room kind lookup.
            size = array_random(tables.get_table('room', 'room_size'))
            shape = array_random(tables.get_table('room', 'room_shapes'))
            state = array_random(tables.get_table('room', 'room_state'))

            if 'size' not in args:
                args['size'] = state
            if 'description' not in args or not args['description']:
                args['description'] = [f"The room is {args['size']} and {shape}-shaped."]
            else:
                # go through the description and fill in the size, shape, and
                # state values in any descriptive text
                args['description'] = [template(x, {'size': size, 
                                                    'state': state, 
                                                    'shape': shape}) for x in args['description']]

        # TODO: handle flags...
        for f in args['flags']:
            logger.debug(f"Dont' know how to handle flag: {f}")

        return Room(**args)        

    def hide_key(self, key):
        # for now, just hide it in the...um...contents
        self.contents.append(key)




