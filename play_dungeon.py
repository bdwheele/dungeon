#!/bin/env python3

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GObject, GdkPixbuf
from pathlib import Path
from dungeon.dungeon import Dungeon
import yaml
import logging
import argparse
import sys
from dungeon.ui.dialogs import DialogUser
from dungeon.ui.objectwidget import ObjectWidget
from dungeon.utils import roll_dice
from dungeon.ui.uiutils import frame_wrap
import tempfile
import subprocess
import os
import re
import random

logger = logging.getLogger()

class PlayDungeon(Gtk.Application, DialogUser):
    def __init__(self):
        Gtk.Application.__init__(self)
        builder = Gtk.Builder()
        builder.add_objects_from_file(sys.path[0] + "/ui/windows.glade", 
                                      ('mainWindow', 'imgParty', 'imgInventory',
                                       'imgTree', 'imgMap', 'imgSkeletonKey',
                                       'inventoryWindow', 'treeWindow', 'imgRun'))
        builder.connect_signals(self)
        self.builder = builder
        # find the objects we care about
        self.window = builder.get_object('mainWindow')
        self.mapImage = builder.get_object('mapImage')
        #self.mapImage.modify_bg(Gtk.StateType.NORMAL, Gdk.Color.parse("white")[1])
        self.mapImage.modify_bg(Gtk.StateType.NORMAL, Gdk.RGBA(1.0, 1.0, 1.0, 1.0).to_color())
        self.roomLabel = builder.get_object('roomLabel')
        self.visitedLabel = builder.get_object('visitedLabel')
        self.detailsPanel = builder.get_object('detailsPanel')
        self.exitsPanel = builder.get_object('exitsPanel')
        self.monstersPanel = builder.get_object('monstersPanel')
        self.dungeonTime = builder.get_object('dungeonTime')
        # variables
        self.dungeon = None
        self.dungeon_filename = None
        self.all_map = False
        self.tree_scale = 0
        self.tree_svg = None
        self.map_scale = 0
        self.map_svg = None
        self.scales = [1, 1.5, 2, 0.75, 0.50]
        self.window.show()


    def onNew(self, caller):
        print("on file new")

    def onOpen(self, caller):
        new_filename = self.file_dialog(mode='r', title="Choose a dungeon file")
        if new_filename is not None:
            try:
                self.load_dungeon(new_filename)
            except Exception as e:
                self.message_box(Gtk.MessageType.ERROR, "Open Failed", e)

    def onSave(self, caller):
        new_name = self.dungeon_filename
        if new_name is None:
               self.onSaveAs(caller, 'untitled.dng')
        else:
            try: 
                with open(new_name, 'w') as f:
                    yaml.dump(self.dungeon, stream=f)
                self.dungeon_filename = new_name
                self.window.set_title(f"Play Dungeon: {new_name}")
            except Exception as e:
                self.message_box(Gtk.MessageType.ERROR, "Save Failed", e)

    def onSaveAs(self, caller, suggested=None):
        new_filename = self.file_dialog(mode='w', suggested_name=suggested, title="Save Dungeon")
        if new_filename is not None:
            self.dungeon_filename = new_filename
            self.onSave(caller)

    def onParty(self, caller):
        print("on party")

    def onInventory(self, caller):
        if not self.dungeon.inventory.contents:
            self.message_box(Gtk.MessageType.INFO, "Inventory", "There are no items in the inventory")
            return

        value = self.dungeon.inventory.get_value()
        window = self.builder.get_object('inventoryWindow')
        label = self.builder.get_object('lblInventory')
        label.set_markup(f"<b>Inventory (value: {value:0.2f}gp)</b>")
        box = self.builder.get_object('boxInventory')
        for o in box.get_children():
            box.remove(o)

        for i in self.dungeon.inventory.contents:
            ow = ObjectWidget(self.dungeon, i, controls=False)
            frame = frame_wrap(ow, f"{i.class_label()} {i.id}",
                               hpad=5, vpad=0, hmargin=10, vmargin=5)
            box.pack_start(frame, True, True, 0)
        window.show()
        window.run()
        window.hide()


    def onMap(self, caller):
        self.all_map = caller.get_active()
        self.onUpdateData(caller)

    def onTree(self, caller):
        window = self.builder.get_object("treeWindow")
        def hide_tree_window(caller, event):
            caller.hide()
            return True
        window.connect('delete-event', hide_tree_window)
        def zoom_tree_window(caller, event):
            if event.string == '-':
                self.tree_scale = max(-2, self.tree_scale - 1)
            elif event.string == '+':
                self.tree_scale = min(2, self.tree_scale + 1)
            self.updateTree()
        window.connect('key_press_event', zoom_tree_window)
        window.show()

    def updateTree(self):
        factor = self.scales[self.tree_scale]
        loader = GdkPixbuf.PixbufLoader()
        # Get the size of the svg
        if m := re.search(r'viewBox="(.+?)\s+(.+?)\s+(.+?)\s+(.+?)"', str(self.tree_svg)):
            loader.set_size(float(m.group(3)) * factor, float(m.group(4)) * factor)
        loader.write(self.tree_svg)
        loader.close()
        pixbuf = loader.get_pixbuf()
        self.builder.get_object("treeImage").set_from_pixbuf(pixbuf)

    def updateMap(self):
        factor = self.scales[self.map_scale]
        loader = GdkPixbuf.PixbufLoader()
        # Get the size of the svg
        if m := re.search(r'viewBox="(.+?)\s+(.+?)\s+(.+?)\s+(.+?)"', str(self.map_svg)):
            loader.set_size(float(m.group(3)) * factor, float(m.group(4)) * factor)
        loader.write(self.map_svg)
        loader.close()
        pixbuf = loader.get_pixbuf()
        self.mapImage.set_from_pixbuf(pixbuf)

    def onKeyPress(self, caller, event):
        if event.string == '-':
            self.map_scale = max(-2, self.map_scale - 1)
        elif event.string == '+':
            self.map_scale = min(2, self.map_scale + 1)
        self.updateMap()

    def onSkeletonKey(self, caller):
        self.dungeon.state['skeleton_key'] = caller.get_active()

    def onRunTo(self, caller):
        # update the run-to menu
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_hexpand(True)
        flowbox = Gtk.FlowBox()
        flowbox.set_valign(Gtk.Align.START)
        flowbox.set_max_children_per_line(5)
        flowbox.set_selection_mode(Gtk.SelectionMode.NONE)
        scrolled.add(flowbox)
        menu = Gtk.Popover()
        menu.set_size_request(240, 150)
        menu.add(scrolled)
        if self.all_map:
            rooms = [x for x in self.dungeon.objects.values() if x.is_a('Room')]
        else:
            rooms = [x for x in self.dungeon.objects.values() if x.is_a('Room') and x.visited]
        for r in sorted(rooms, key=lambda x: int(x.id[1:])):
            x = Gtk.Button(label=r.id)
            x.connect('clicked', self.onRunToChoice)
            flowbox.add(x)
        menu.set_relative_to(caller)
        menu.set_position(Gtk.PositionType.BOTTOM)
        menu.show_all()
        menu.popup()
        self.runtopopup = menu

    def onRunToChoice(self, caller):
        logger.debug(f"User has run to room {caller.get_label()}")
        self.dungeon.state['current_room'] = self.dungeon.objects[caller.get_label()]
        self.dungeon.state['current_room'].visited = True
        self.runtopopup.popdown()
        self.onUpdateData(caller)

    def onDestroyWindow(self, caller, something):
        if self.ok_cancel_dialog(Gtk.MessageType.QUESTION, "Quit Application?", 
                                 "Any progress you have made since the last save will be lost"):
            Gtk.main_quit()
        return True

    def load_dungeon(self, filename):
        with open(filename, 'r') as f:
            self.dungeon = yaml.load(f, Loader=yaml.FullLoader)
        self.dungeon_filename = filename
        self.window.set_title(f"Play Dungeon: {filename}")
        self.onUpdateData(None)

    def onUpdateData(self, caller):
        """ Update all of the data elements """
        if self.dungeon == None:
            return

        # generate the map image
        dot = self.dungeon.generate_map_dot(all_rooms=self.all_map).encode('utf-8')
        p = subprocess.run(['neato', '-Tsvg'], input=dot, stdout=subprocess.PIPE, check=True)
        self.map_svg = p.stdout
        self.updateMap()

        dot = self.dungeon.generate_object_graph_dot().encode('utf-8')
        p = subprocess.run(['neato', '-Tsvg'], input=dot, stdout=subprocess.PIPE, check=True)
        self.tree_svg = p.stdout
        self.updateTree()


        # update the panels.
        current_room = self.dungeon.state['current_room']
        panels = [
            [self.detailsPanel, [current_room], False],
            [self.exitsPanel, list(x for x in current_room.contents if x.is_a('Door')), True],
            [self.monstersPanel, list(x for x in current_room.contents if x.is_a('Monster')), True]
        ]
        for panel, contents, use_frame in panels:
            for c in panel.get_children():
                panel.remove(c)
            for c in contents:
                ow = ObjectWidget(self.dungeon, c)
                ow.connect('update_data', self.onUpdateData)
                ow.connect('update_time', self.onUpdateTime)
                ow.show()
                if use_frame:
                    flag = " \u2714 " if c.is_a('Door') and c.visited else "" 
                    frame = frame_wrap(ow, f"{c.class_label()} {c.id}{flag}")
                    panel.add(frame)
                else:
                    panel.add(ow)

        # update other information
        self.roomLabel.set_label(f"{current_room.class_label()} {current_room.id}")
        count = 0
        visited = 0
        for o in self.dungeon.objects.values():
            if o.is_a('Room'):
                count += 1
                if o.visited:
                    visited += 1
        self.visitedLabel.set_label(f"Rooms visited: {visited}/{count}")


    def onUpdateTime(self, caller, time):
        state = self.dungeon.state
        state['current_time'] += time
        total = state['current_time']
        days = total // (24 * 60)
        total -= days * (24 * 60)
        hours = total // 60
        mins = total - hours * 60
        if days:
            t = f"{days}+{hours:02d}:{mins:02d}"
        else:
            t = f"{hours:02d}:{mins:02d}"
        self.dungeonTime.set_label(t)

        # handle wandering monsters
        if 'next_wandering_monster' not in state:
            state['next_wandering_monster'] = total + 10 + random.randint(1, 30)

        if total > state['next_wandering_monster']:
            # we're due for a monster, maybe.
            logger.debug("check for wandering monster")
            if random.randint(0, 3) <= self.dungeon.parameters['wandering_monsters']['percent_chance']:
                logger.debug("Monster will appear")
                print("*** TODO ***")
            state['next_wandering_monster'] = total + 10 + random.randint(1, 30)
            logger.debug(f"Next wandering monster after {state['next_wandering_monster']}")
        

        







def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("dungeon", metavar="<dungeon>", nargs='?', default=None, help="Load a dungeon at start")
    parser.add_argument("--debug", default=False, action='store_true', help="Turn on debugging")
    args = parser.parse_args()

    logger.setLevel(logging.DEBUG if args.debug else logging.INFO)
    log_handler =logging.StreamHandler(sys.stderr)
    log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    log_handler.setFormatter(log_formatter)
    logger.addHandler(log_handler)

    app = PlayDungeon()
    if args.dungeon is not None:
        app.load_dungeon(args.dungeon)  
    Gtk.main()


if __name__ == "__main__":
    main()

