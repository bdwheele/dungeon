import random
import logging
from pathlib import Path
import yaml
import copy

logger = logging.getLogger()

class Tables:
    """
    Manage the tables for a specific style by loading the configuration
    files and then provding access functions
    """
    def __init__(self, root, style="default"):
        self.root = Path(root)
        if not self.root.is_dir():
            raise ValueError("Root directory doesn't exist")        
        self.set_style(style)

    def get_styles(self):
        """
        Get the styles which are available at the root
        """
        return [str(f.stem) for f in self.root.iterdir() if f.is_dir()]

    def set_style(self, style):
        """
        Set the style which will be used for all table lookups,
        clearing all of the caches.
        """
        styledir = self.root.joinpath(style)
        if not styledir.is_dir():
            raise ValueError(f"Style directory {styledir} doesn't exist")

        self.search = [styledir, self.root.joinpath("default")]
        self.stash = {}
        self.style = style

    def get_groups(self):
        """
        Get the available groups for the current style
        """
        groups = set()
        for p in self.search:
            for g in p.iterdir:
                groups.add(g.stem)
        return groups

    def get_group(self, group):
        """
        Find a group and return it, loading it from the disk if needed
        """
        if group not in self.stash:
            filebase = group + ".yaml"            
            for p in self.search:
                filename = p.joinpath(filebase)
                if filename.exists():
                    break
            else:
                raise FileNotFoundError(f"Cannot find table file for group {group}")
                    
            with open(filename) as f:
                self.stash[group] = yaml.safe_load(f)
        return self.stash[group]

    def get_tables(self, group):
        """
        Get the tables that are in the group in question
        """
        g = self.get_group(group)
        return g.keys()

    def get_table(self, group, table):
        """
        Get a specific table
        """
        g = self.get_group(group)
        if table not in g:
            raise KeyError(f"Table {table} doesn't exist in group {group}")
        return g[table]                    



