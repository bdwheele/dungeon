class Container:
    def __init__(self):
        self.can_contain = False
        self.contents = []

    def store(self, thing):
        if not self.can_contain:
            raise ValueError(f"This object cannot be used as a container")
        self.contents.append(thing)

    def discard(self, thing):
        self.contents.remove(thing)
    