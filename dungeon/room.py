
import logging
from .dobject import DObject
from .mergeable import Mergeable
from .container import Container
from .trappable import Trappable
from .inspectable import Inspectable
from .utils import gen_id, array_random, template


logger = logging.getLogger()

class Room(DObject, Container, Trappable, Inspectable):
    def __init__(self, **kwargs):
        DObject.__init__(self)
        Container.__init__(self)
        self.can_contain = True
        self.container_open = True
        Trappable.__init__(self)
        Inspectable.__init__(self)

        # general room/corridor stuff
        self.is_corridor = False
        self.visited = False
        self.size = None
        self.size_integer = -1
        self.merge_attrs(kwargs)

    def __str__(self):
        doors = [str(x) for x in self.contents if x.is_a('Door')]
        return f"Room(id={self.id}, description={self.description}, doors={doors})"

    def decorate(self, tables):
        door_count = len([x for x in self.contents if x.is_a("Door")])
        # determine if this is a room or a corridor
        self.is_corridor = 'corridor' == array_random(tables.get_table('room', 'room_type'))
        if self.is_corridor:
            if door_count == 1:
                self.merge_attrs(array_random(tables.get_table('room', 'corridor_ends')))
            elif door_count == 2:
                self.merge_attrs(array_random(tables.get_table('room', 'corridor_through')))
            else:
                self.description = [f"The corridor branches into {door_count} routes, including the one you came from"]
        else:
            # get the room kind.  This may carry along other attributes
            self.merge_attrs(array_random(tables.get_table('room', 'room_kind')))
    
            # fill in any details that didn't come from the room kind lookup.
            size = array_random(tables.get_table('room', 'room_size'))
            shape = array_random(tables.get_table('room', 'room_shape'))
            state = array_random(tables.get_table('room', 'room_state'))

            if self.size is None:
                self.size = size

            self.size_integer = tables.get_table('room', 'size_to_integer').get(self.size, -2)
            if not self.description:
                self.description = [f"The room is {self.size} and {shape}-shaped."]
            else:
                # go through the description and fill in the size, shape, and
                # state values in any descriptive text
                self.description = [template(x, {'size': size, 
                                                 'state': state, 
                                                 'shape': shape}) for x in self.description]






