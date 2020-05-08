# The object can have a trap

class Trappable:
    def __init__(self):
        self.has_trap = False
        self.trap_found = False
        self.trap = None


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
    