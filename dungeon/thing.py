from .lockable import Lockable
from .container import Container
from .mergeable import Mergeable
from .inspectable import Inspectable
from .utils import gen_id

class Thing(Lockable, Container, Mergeable, Inspectable):
    def __init__(self):
        self.id = None
        self.is_portable = False
        self.location = None
        self.description = []
        self.flags = []
        Lockable.__init__(self)
        Container.__init__(self)
        Inspectable.__init__(self)
        