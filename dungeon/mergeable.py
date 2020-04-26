#
# Merge a dict into the attributes of an object, doing the right things
# when hitting arrays and dicts.
#
class Mergeable:
    def merge_attrs(self, attrs):
        for k, v in attrs.items():
            if hasattr(self, k):
                a = getattr(self, k)
                if isinstance(a, list):
                    if isinstance(v, (list, tuple)):
                        a.extend(v)
                    else:
                        a.append(v)
                elif isinstance(a, dict):
                    if isinstance(v, dict):
                        a.update(v)
                    else:
                        raise ValueError(f"Cannot merge a {type(v)} into a {type(a)}")
                else:
                    # straight replacement
                    setattr(self, k, v)
