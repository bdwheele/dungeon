from .mergeable import Mergeable
from .utils import gen_id
from copy import deepcopy
import re

class DObject(Mergeable):
    prefixes = {}
    """
    This is the base class for all things in a dungeon, including rooms,
    doors, keys, monsters, etc.  Pretty much everything.
    """
    def __init__(self, **kwargs):
        self.id = None # gen_id('dobject', prefix=self._get_prefix())
        self.description = []
        self.flags = []
        self.location = None
        self.is_hidden = 0
        self.merge_attrs(kwargs)

    def __str__(self):
        return f"{type(self).__name__}(id={self.id}, description={self.description[0]})"

    def _get_prefix(self):
        name = type(self).__name__
        if name not in DObject.prefixes:
            if name[0] not in DObject.prefixes.values():
                DObject.prefixes[name] = name[0]
            else:
                for x in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
                    if x not in DObject.prefixes.values():
                        DObject.prefixes[name] = x
                        break
        return DObject.prefixes[name]

    def clone(self):
        new = deepcopy(self)
        #new.id = gen_id('dobject', prefix=new.id[0])
        return new

    def class_label(self):
        return type(self).__name__

    def is_a(self, *classes):
        """
        Do the equivalent of isinstance() except take string class names.
        This way, I don't have to import the class for the object that I'm 
        only passing around.
        """
        if not classes:
            # If they didn't specify, then ... yes it is
            return True

        names = []
        for c in classes:
            if isinstance(c, str):
                names.append(c)
            else:
                names.append(c.__name__)
        search = set(names)
        if search.intersection(set([x.__name__ for x in type(self).__mro__])):
            return True
        return False

    def find_ancestor(self, *classes):
        """
        Find an ancestor that is in one of the specified classes
        """
        if self.location is None:
            return None
        if self.location.is_a(classes):
            return self.location
        return self.location.find_parent(classes)


    def decorate(self, tables):
        """
        Do any post-creation decoration of the object.
        """
        pass


    def get_value(self, recursive=True):
        exchange = {'c': 0.01, 's': 0.1, 'e': 0.5, 'g': 1.0, 'p': 5.0}
        pat = re.compile(r"(\b(\d+)x\b.+)?\b(\d+)\s*([csegp])p\b", re.IGNORECASE)
        total = 0
        for d in self.description:
            for m in pat.finditer(d):
                multiplier = 1
                if m.group(1):
                    multiplier = int(m.group(2))
                amt = int(m.group(3))
                coin = m.group(4).lower()
                if coin in exchange:
                    total += multiplier * (amt * exchange[coin])
        if recursive and self.is_a('Container'):
            for c in self.contents: #pylint: disable=no-member
                total += c.get_value()

        return total

