class Breakable:
    def __init__(self):
        self.is_breakable = False
        self.is_broken = True
        self.break_dc = 0

    def break_object(self, strength):
        if self.is_broken:
            return True
        if strength >= self.break_dc:
            self.is_broken = True
            return True
        return False