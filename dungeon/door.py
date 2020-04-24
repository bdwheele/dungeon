from yaml import YAMLObject
from .utils import gen_id, array_random
import logging
import math

logger = logging.getLogger()

class Door(YAMLObject):
    def __init__(self, **kwargs):
        # general door/passage stuff
        self.id = None
        self.connections = (-1, -1)
        self.is_passage = False
        self.flags = []
        self.description = []
        self.is_open = True
        self.visited = False
        self.break_down_dc = 0
        # lock
        self.is_locked = False
        self.has_lock = False
        self.needs_key = None
        self.key_description = None
        self.pick_lock_dc = 0
        # stickyness
        self.is_stuck = False
        self.stuck_found = False
        self.stuck_dc = 0
        # trap
        self.has_trap = False
        self.trap_found = False
        self.trap_id = -1

        for k in kwargs:
            if hasattr(self, k):
                setattr(self, k, kwargs[k])


    @staticmethod
    def generate(tables, id, connections):
        # build the arguments and generate the room
        args = {
            'id': id,
            'connections': (connections[0].id, connections[1].id)
        }

        type_table = "room_to_corridor"
        if connections[0].is_corridor == connections[1].is_corridor:
            if connections[0].is_corridor:
                type_table = "corridor_to_corridor"
            else:
                type_table = "room_to_room"
        args['is_passage'] = 'passage' == array_random(tables.get_table("door", type_table))
        if args['is_passage']:
            # decorate the passage
            args.update(array_random(tables.get_table('door', 'passage')))
        else:
            # decorate the door
            args.update(array_random(tables.get_table('door', 'door_material')))
            if 'flags' not in args:
                args['flags'] = []
            args['flags'].extend(array_random(tables.get_table('door', 'door_flags')))

        # TODO: handle flags.
        if 'flags' in args:
            for f in args['flags']:
                if f == 'STUCK':
                    args['is_stuck'] = True
                    args['stuck_dc'] = math.floor(args['break_down_dc'] / 2)
                elif f == 'LOCKED':
                    args['has_lock'] = True
                    args['is_locked'] = True
                    args['pick_lock_dc'] = 3 # TODO
                    args['needs_key'] = gen_id('key', random=True, prefix='K')
                    material = array_random(tables.get_table('door', 'key_material'))
                    size = array_random(tables.get_table('door', 'key_size'))
                    description = f"{size}-sized key made of {material}"
                    args['description'].append(f"The lock requires a {description} to lock or unlock")
                    args['key_description'] = description
                elif f == 'TRAP':
                    args['has_trap'] = True
                    # TODO:  build a trap and put it in!
                    pass
                else:
                    logger.debug(f"Don't know how to decorate door with flag {f}")

        return Door(**args)



    ###
    ### Run-time behavior
    ###
    def valid_key(self, key):
        return key == self.needs_key or key == 'skeleton'

    def unlock(self, key):
        if not self.has_lock:
            return (False, "This door doesn't have a lock")
        self.trigger_trap('use')
        if not self.valid_key(key):
            return (False, "This key will not work in this lock")
        self.is_locked = False
        return (True, "Door is unlocked")

    def lock(self, key): 
        if not self.has_lock:
            return (False, "Door does not have a lock")
        if self.is_open:
            return (False, "Cannot lock an open door")
        if not self.valid_key(key):
            return (False, "This key will not work with this door")
        self.is_locked = True
        return (True, "The door is locked")

    def pick(self, dex):
        if not self.has_lock:
            return (True, "Door has no lock")
        if self.is_open:
            return (True, "Door is already open")
        if not self.is_locked:
            return (True, "Door is already unlocked")
        self.trigger_trap('use')
        if dex >= self.pick_lock_dc:
            self.is_locked = False
            return (True, "Lock has been picked")
        else:
            return (False, "Lock was not picked successfuly")

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
            new_room = self.connections[0] if self.connections[1] == current_room else self.connections[1]
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
        new_room = self.connections[0] if self.connections[1] == current_room else self.connections[1]
        return (True, "Door/Passage has been used", new_room)

    def detect_trap(self, perception):
        self.trigger_trap('detect')
        # TODO: Actual detection
        self.trap_found = True
        return (True, 'successfully detected trap')

    def disarm_trap(self, dexterity):
        # TODO: Disarm trap
        self.trigger_trap('disarm')
        self.has_trap = False
        return (True, "Trap disarmed")

    def trigger_trap(self, mode):
        """ Trigger the trap """
        if not self.has_trap:
            return
        #if self.has_trap and mode in self.attributes['trap']['triggers']:
        #    percent = self.attributes['trap']['triggers']
        #else:
        #    raise ValueError(f"Don't know how to trigger trap with mode {mode}")
        ### TODO:  compute probabilty and trigger the trap.
