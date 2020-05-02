from .utils import gen_id, array_random
import logging
import math
from .dobject import DObject
from .lockable import Lockable
from .trappable import Trappable
from .breakable import Breakable
from .inspectable import Inspectable

logger = logging.getLogger()

class Door(DObject, Lockable, Trappable, Breakable, Inspectable):
    def __init__(self, **kwargs):
        DObject.__init__(self, **kwargs)
        # general door/passage stuff
        self.sides = []
        self.is_passage = False
        self.is_open = False
        self.visited = False
        # stickyness
        self.is_stuck = False
        self.stuck_found = False
        self.stuck_dc = 0

        Breakable.__init__(self)
        Lockable.__init__(self)
        Trappable.__init__(self)
        Inspectable.__init__(self)

        self.merge_attrs(kwargs)

    def __str__(self):
        return f"Door(id={self.id}, description={self.description}, has_trap={self.has_trap}, has_lock={self.has_lock}, connects: {[x.id for x in self.sides]})" #pylint: disable=no-member

    def decorate(self, tables):
        # build the arguments and generate the room
        type_table = "room_to_corridor"
        if self.sides[0].is_corridor == self.sides[1].is_corridor:
            type_table = "corridor_to_corridor" if self.sides[0].is_corridor else "room_to_room"
        self.is_passage = 'passage' == array_random(tables.get_table("door", type_table))
        if self.is_passage:
            # decorate the passage
            self.merge_attrs(array_random(tables.get_table('door', 'passage')))
            self.is_open = True
        else:
            # decorate the door
            self.merge_attrs(array_random(tables.get_table('door', 'door_material')))
            self.flags.extend(array_random(tables.get_table('door', 'door_flags')))

    def other_side(self, room):
        if self.sides[0] == room:
            return self.sides[1]
        return self.sides[0]


    ###
    ### Run-time behavior
    ###

    def unlock(self, key):
        if not self.has_lock:
            return (False, "This door doesn't have a lock")
        self.trigger_trap('use')
        return super().unlock(key)


    def lock(self, key): 
        if not self.has_lock:
            return (False, "Door does not have a lock")
        if self.is_open:
            return (False, "Cannot lock an open door")
        return super().lock(key)


    def pick(self, dex):
        if not self.has_lock:
            return (True, "Door has no lock")
        if self.is_open:
            return (True, "Door is already open")
        return super().pick(dex)


    def open(self):
        if self.is_open:
            return (True, "Door is already open")
        self.trigger_trap('use')
        if self.is_locked:
            return (False, "Door is locked")
        self.stuck_found = True
        if self.is_stuck:
            return (False, "Door is stuck closed")
        self.is_open = True
        return (True, "Door is open")

    def close(self):
        if self.is_stuck:
            self.stuck_found = True
            return (False, "Door is stuck open")
        self.is_open = False
        return (True, "Door is closed")

    def force_open(self, strength, current_room):
        if self.is_open:
            return (True, "Door is already open", None)
        if strength >= self.stuck_dc:
            self.trigger_trap('force')
            self.is_open = True
            self.stuck_found = True
            self.is_stuck = False
            self.is_locked = False
            self.visited = True
            new_room = self.other_side(current_room)
            return (True, "Successfully forced door open", new_room)
        else:
            return (False, "Attempt to break open door fails", None)

    def force_close(self, strength):
        if not self.is_open:
            return (True, "Door is already closed")
        if strength >= self.stuck_dc:
            self.is_open = False
            self.is_stuck = False

    def make_stuck(self):
        self.is_stuck = True
        return (True, "Door is now stuck")

    def use(self, current_room):
        if not self.is_passage:
            if not self.is_open:
                self.trigger_trap('use')
                if self.is_locked:
                    return (False, "Door is locked", None)
                self.stuck_found = True
                if self.is_stuck:
                    return (False, "Door is stuck", None)
                self.is_open = True
        self.visited = True
        new_room = self.sides[0] if self.sides[1] == current_room else self.sides[1]
        return (True, "Door/Passage has been used", new_room)
