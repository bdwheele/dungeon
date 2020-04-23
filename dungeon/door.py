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
            args['flags'].extend(array_random(tables.get_table('door', 'door_flags'))['flags'])

        # TODO: handle flags.
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
                # TODO:  put the key in the room
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


    def is_key(self, key):
        print(f"Key={key}, {self.attributes['key'][0]}")
        return key == str(self.attributes['key'][0]) or key == "skeleton"

    def get_key(self):
        return self.attributes['key']

    def has_lock(self):
        return 'LOCKED' in self.attributes['flags']

    def is_locked(self):
        return self.attributes['state']['locked']

    def unlock(self, key):
        if not self.has_lock():
            return (False, "This door doesn't have a lock")
        self.trigger_trap('use')
        if not self.is_key(key):
            return (False, "This key will not work in this lock")
        self.attributes['state']['locked'] = False
        return (True, "Door is unlocked")

    def lock(self, key): 
        if not self.has_lock():
            return (False, "Door does not have a lock")
        if self.is_open():
            return (False, "Cannot lock an open door")
        if not self.is_key(key):
            return (False, "This key will not work with this door")
        self.attributes['state']['locked'] = True
        return (True, "The door is locked")

    def pick(self, dex):
        if not self.has_lock():
            return (True, "Door has no lock")
        if self.is_open():
            return (True, "Door is already open")
        if not self.is_locked():
            return (True, "Door is already unlocked")
        self.trigger_trap('use')
        if dex >= self.attributes['dc']:
            self.attributes['state']['locked'] = False
            return (True, "Lock has been picked")
        else:
            return (False, "Lock was not picked successfuly")

    def is_open(self):
        return self.type == Edge.PASSAGE or self.attributes['state']['open']

    def open(self):
        if self.is_open():
            return (True, "Door is already open")
        self.trigger_trap('use')
        if self.is_locked():
            return (False, "Door is locked")
        self.attributes['state']['stuck_found'] = True
        if self.is_stuck():
            return (False, "Door is stuck closed")
        self.attributes['state']['open'] = True
        return (True, "Door is open")

    def close(self):
        if self.is_stuck():
            return (False, "Door is stuck open")
        self.attributes['state']['open'] = False
        return (True, "Door is closed")

    def force_open(self, strength, current_room):
        if self.is_open():
            return (True, "Door is already open", None)
        if strength >= self.attributes['dc']:
            self.trigger_trap('force')
            self.attributes['state']['open'] = True
            self.attributes['state']['stuck_found'] = True
            self.attributes['state']['stuck'] = False
            self.attributes['state']['locked'] = False
            self.attributes['state']['visited'] = True
            new_room = self.left if self.right == current_room else self.right
            return (True, "Successfully forced door open", new_room)
        else:
            return (False, "Attempt to break open door fails", None)

    def force_close(self, strength):
        if not self.is_open():
            return (True, "Door is already closed")
        if strength >= self.attributes['dc']:
            self.attributes['state']['open'] = False
            self.attributes['state']['stuck'] = False

    def is_stuck(self):
        return self.attributes['state']['stuck']

    def stuck_found(self):
        return self.attributes['state']['stuck_found']

    def make_stuck(self):
        self.attributes['state']['stuck'] = True
        return (True, "Door is now stuck")

    def use(self, current_room):
        if self.type == Edge.DOOR:
            if not self.is_open():
                self.trigger_trap('use')
                if self.is_locked():
                    return (False, "Door is locked", None)
                self.attributes['state']['stuck_found'] = True
                if self.is_stuck():
                    return (False, "Door is stuck", None)
                self.attributes['state']['open'] = True
        self.attributes['state']['visited'] = True
        new_room = self.left if self.right == current_room else self.right
        return (True, "Door/Passage has been used", new_room)

    def has_trap(self):
        return self.attributes['state']['trap']

    def trap_found(self):
        return self.attributes['state']['trap_found']

    def detect_trap(self, perception):
        self.trigger_trap('detect')
        # TODO: Actual detection
        self.attributes['state']['trap_found'] = True
        return (True, 'successfully detected trap')

    def disarm_trap(self, dexterity):
        # TODO: Disarm trap
        self.trigger_trap('disarm')
        self.attributes['state']['trap'] = False
        return (True, "Trap disarmed")

    def trigger_trap(self, mode):
        """ Trigger the trap """
        if not self.has_trap():
            return
        if self.attributes['trap'] is not None and mode in self.attributes['trap']['triggers']:
            percent = self.attributes['trap']['triggers']
        else:
            raise ValueError(f"Don't know how to trigger trap with mode {mode}")
        ### TODO:  compute probabilty and trigger the trap.
