
class Container:
    def __init__(self):
        self.can_contain = False
        self.container_open = False
        self.contents = []

    def store(self, thing):
        if not self.can_contain:
            raise ValueError(f"This object ({self}) cannot be used as a container")
        #print(f"Storing {thing} into {self}")
        thing.location = self
        self.contents.append(thing)

    def discard(self, thing):
        thing.location = None
        self.contents.remove(thing)
    
    def transfer(self, thing, destination):
        self.discard(thing)
        destination.store(thing)

    def find_decendents(self, *classes):
        """Get my contents and the contents of the children.  And their
           children's children.  For three months."""
        result = []
        for x in self.contents:
            if x.isa(classes):
                result.append(x)
            if x.isa('Container'):
                result.extend(x.find_decendents(classes))
        return result


    def open(self):
        if self.container_open or not self.can_contain:
            return False
        self.container_open = True
        # if the container has a monster, then we need to have it jump
        # out -- which means that any monsters in our contents need to
        # be discarded and the monster moved to the containing room.
        room = self.find_ancestor('Room') #pylint: disable=no-member
        room_changed = False
        for c in self.contents:
            if c.is_a('Monster'):
                self.discard(c)
                room.store(c)
                room_changed = True
        return room_changed

