# The object can be locked.

class Lockable:
    def __init__(self):
        self.has_lock = False
        self.is_locked = False
        self.lock_key = None
        self.lock_code = None
        self.lock_pick_dc = 0


    def get_description(self):
        return [f'This lock requires a {self.lock_key.description[0]} key to operate']

    def valid_key(self, key):
        return key == self.lock_code or key == 666

    def unlock(self, key):
        if not self.valid_key(key):
            return (False, "This key will not work in this lock")
        self.is_locked = False
        return (True, "Lock is now unlocked")

    def lock(self, key): 
        if not self.valid_key(key):
            return (False, "This key will not work with this lock")
        self.is_locked = True
        return (True, "The lock is locked")

    def pick(self, dex):
        if not self.is_locked:
            return (True, "Lock is already unlocked")
        if dex >= self.lock_pick_dc:
            self.is_locked = False
            return (True, "Lock has been picked")
        else:
            return (False, "Lock was not picked successfuly")
