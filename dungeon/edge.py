import logging
from .utils import mergedata, gen_id
import copy

logger = logging.getLogger()

class Edge:
    UNTYPED = 0
    DOOR = 1
    PASSAGE = 2

    def __init__(self, left, right, etype=0):
        self.id = gen_id('edge')
        self.type = etype
        self.left = left
        self.right = right
        self.attributes = {}

    @staticmethod
    def load(data):
        "restore an edge from a dict"
        e = Edge(data['left'], data['right'], data['type'])
        e.id = data['id']
        e.attributes = data['attributes']
        return e

    def save(self):
        "dump the edge as a dict"
        return {
            'id': self.id,
            'type': self.type,
            'left': self.left,
            'right': self.right,
            'attributes': self.attributes
        }

    def connects(self, lnode, rnode):
        return ((self.left == lnode and self.right == rnode) or
                (self.left == rnode and self.right == lnode))
        

    ###
    ### Things dealing with attributes
    ###
    def decorate(self, tables):
        # set the defaults for all of the attributes
        self.attributes = {
            'description': [],
            'flags': [],
            'dc': 0,
            'trap': None,
            'key': None,        
            'state': {
                'locked': False,
                'open': False,
                'stuck': False,
                'stuck_found': False,
                'trap': False,
                'trap_found': False,
                'visited': False
            },
        }

        if self.type == Edge.DOOR:
            mergedata(self.attributes, tables.random("decorate_door", "type"))

            door_special = tables.random("decorate_door", "special")
            if door_special in ['side', 'down']:
                self.attributes['dc'] += 1
                self.attributes['description'].append(f"The door slides {door_special}")

            elif door_special == 'up':
                self.attributes['dc'] += 2    
                self.attributes['description'].append(f"The door slides {door_special}")

            elif door_special == 'magical':
                self.attributes['flags'].append('MAGIC')
                self.attributes['dc'] += 4

        elif self.type == Edge.PASSAGE:
            mergedata(self.attributes, tables.random('decorate_passage', 'type'))


        # TODO: handle the flags for everything
        for f in self.attributes['flags']:
            if f == 'STUCK':
                self.attributes['state']['stuck'] = True
            elif f == 'LOCKED':
                self.attributes['state']['locked'] = True
                # generate a key...
                key_type = tables.random('decorate_door', 'key_material')
                key_size = tables.random('decorate_door', 'key_size')
                self.attributes['description'].append(f"The lock on the door appears to take a {key_size}-sized key made of {key_type}")
                k_id = gen_id('locks', random=True)
                self.attributes['key'] = (k_id, f"A {key_size}-sized key made of {key_type} ({k_id})")
            elif f == 'TRAP':
                # TODO: create the trap
                pass



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
    