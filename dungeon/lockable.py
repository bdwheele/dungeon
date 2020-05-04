# The object can be locked.

class Lockable:
    def __init__(self):
        self.has_lock = False
        self.is_locked = False
        self.lock_key = None
        self.lock_pick_dc = 0


    def get_key_description(self):
        return [f'This lock requires a {self.lock_key.description[0]} key to operate']

    def valid_key(self, key):
        return key == self.lock_key

    def pick(self, dex):
        if not self.is_locked:
            return (True, "Lock is already unlocked")
        if dex >= self.lock_pick_dc:
            self.is_locked = False
            return (True, "Lock has been picked")
        else:
            return (False, "Lock was not picked successfuly")
