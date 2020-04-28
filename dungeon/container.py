
class Container:
    def __init__(self):
        self.can_contain = True
        self.container_open = False
        self.contents = []

    def store(self, thing):
        if not self.can_contain:
            raise ValueError(f"This object cannot be used as a container")
        print(f"Storing {thing} into {self}")
        thing.location = self
        self.contents.append(thing)

    def discard(self, thing):
        self.contents.remove(thing)
    
    def get_recursive_contents(self):
        """Get my contents and the contents of the children.  And their
           children's children.  For three months."""
        result = []
        for x in self.contents:
            result.append(x)
            if isinstance(x, Container) and x.can_contain:
                result.extend(x.get_recursive_contents())
        return result



    def open(self):
        if self.container_open:
            return False
        self.container_open = True
        # if the container has a monster, then we need to have it jump
        # out -- which means that any monsters in our contents need to
        # be discarded and the monster moved to the containing room.
        room = self.find_room_ancestor()
        room_changed = False
        for c in self.contents:
            # TODO: verify this -- make sure monster class is the only one with 'move()'
            if callable(getattr(c, 'move', None)):
                self.discard(c)
                room.store(c)
                room_changed = True
        return room_changed

    def find_room_ancestor(self):
        here = self
        while not here.id.startswith("R"): #pylint: disable=no-member
            here = here.location #pylint: disable=no-member
        return here