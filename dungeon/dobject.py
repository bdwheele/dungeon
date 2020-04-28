from .mergeable import Mergeable
from .utils import gen_id


class DObject(Mergeable):
    prefixes = {}
    """
    This is the base class for all things in a dungeon, including rooms,
    doors, keys, monsters, etc.  Pretty much everything.
    """
    def __init__(self, **kwargs):
        self.id = gen_id('dobject', prefix=self._get_prefix())
        self.description = []
        self.flags = []
        self.merge_attrs(kwargs)

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

    def is_a(self, *classes):
        """
        Do the equivalent of isinstance() except take string class names.
        This way, I don't have to import the class for the object that I'm 
        only passing around.
        """
        if not classes:
            raise ValueError("You must supply at least one class to check for")

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

    def decorate(self, tables):
        """
        Do any post-creation decoration of the object.
        """
        pass