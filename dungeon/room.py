from .utils import gen_id, array_random, template
import logging
from .mergeable import Mergeable
from .container import Container
from .trappable import Trappable

logger = logging.getLogger()

class Room(Mergeable, Container, Trappable):
    def __init__(self, **kwargs):
        # general room/corridor stuff
        self.id = None
        self.is_start = False
        self.doors = []
        self.is_corridor = False
        self.flags = []
        self.description = []
        self.visited = False
        self.size = None
        self.size_integer = -1
        Trappable.__init__(self)
        Container.__init__(self)
        self.can_contain = True

        self.merge_attrs(kwargs)

    def __str__(self):
        return f"Room(id={self.id}, description={self.description}, doors={[str(d) for d in self.doors]})"

    @staticmethod
    def generate(tables, id, door_count):
        # build arguments and create the room.
        room = Room(id=id)

        # determine if this is a room or a corridor
        room.is_corridor = 'corridor' == array_random(tables.get_table('room', 'room_type'))
        if room.is_corridor:
            if door_count == 1:
                room.merge_attrs(array_random(tables.get_table('room', 'corridor_ends')))
            elif door_count == 2:
                room.merge_attrs(array_random(tables.get_table('room', 'corridor_through')))
            else:
                room.description = [f"The corridor branches into {door_count} routes, including the one you came from"]
        else:
            # get the room kind.  This may carry along other attributes
            room.merge_attrs(array_random(tables.get_table('room', 'room_kind')))
    
            # fill in any details that didn't come from the room kind lookup.
            size = array_random(tables.get_table('room', 'room_size'))
            shape = array_random(tables.get_table('room', 'room_shape'))
            state = array_random(tables.get_table('room', 'room_state'))

            if room.size is None:
                room.size = size

            room.size_integer = tables.get_table('room', 'size_to_integer').get(room.size, -2)
            if not room.description:
                room.description = [f"The room is {room.size} and {shape}-shaped."]
            else:
                # go through the description and fill in the size, shape, and
                # state values in any descriptive text
                room.description = [template(x, {'size': size, 
                                                    'state': state, 
                                                    'shape': shape}) for x in room.description]

        # TODO: handle flags...
        for f in room.flags:
            logger.debug(f"Dont' know how to handle flag: {f}")

        return room        
    def hide_key(self, key):
        # for now, just hide it in the...um...contents
        self.contents.append(key)




