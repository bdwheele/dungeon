# dungeon - A random dungeon creator and GUI for playing non-dedicated-DM sessions

## The problem

My daughter has recently become interested in D&D 5e.  That's cool...I'm an old school BECMI player.

What's not cool is that I never get to play as a player...I always have to be the DM.  But even if she does DM, then we're not really playing together.  

## This solution

So here's my solution to the problem:  the bulk of DM'ing falls into three categories:
* story telling
* creating a dungeon (usually)
* working the game mechanics

This software does the the latter two items.  Or at least parts of those two.

The working theory is that the players take turns (via some method determined by them) on who will be the DM at any given point in the adventure.  

Since nobody knows the details of the dungeon, it becomes a collaborative effort to tell the story.  As rooms are revealed, the players invent the story.  The dungeon-master-for-now would play any monsters encountered.

The software handles some of the more mechanical aspects of running a dungeon:
* revealing the map as explored
* keeping track of the player's inventory
* revealing items based on either passive perception or (via a die roll) active inspection
* locked doors & objects 
* sticky doors (using a strength roll to open)
* rests & time spent in the dungeon
* wandering monsters


## Some details

### The Map

Unlike other dungeon creation tools, the dungeon map is fairly abstract...the rooms may have a generic size (ie. large) in their description, but there aren't any exact dimensions.  

Some generated dungeons may not even be possible to lay out in this universe.  What is important is the connections between the rooms (doors and openings).  From a computer science standpoint, the map is really just an undirected graph, where the nodes are rooms/corridors and the edges are doors/openings.

### Monsters
The monster information really is just the basic details needed to generate the dungeon...along with a reference to the source book and page.  When a monster is encountered, it has to be looked up in a manual for details.

The monster list was compiled from online sources and typing a bunch.

### Tables
All of the generation is based on yaml-based tables which describe pretty much everything.  The tables can (and should) be modified for different kinds of dungeons and scenarios.

Some of the tables were derived from ones in the Dungeon Master's Guide, some from random places on the internet, and others came from my brain.

### Locked items
Locked items appear throughout the generated dungeon.  During generation, the keys are spread out in such a way that the dungeon should be solvable.  Monsters can hold keys, as can other locked items.

## How to use the software

### Main toolbar
#### File Icons
New, Open, Save, and Save as are pretty typical.

New isn't implemented yet, but when finished will allow the user to generate a new dungeon

#### Player controls

* 👥 - set player properties (just passive perception for now)
* 🛒 - show player inventory.  A new window will appear with the inventory and the value of the contents.

#### DM Controls
* 🗺 - show all rooms
* 🌳 - show the object tree.  The +/- keys can be used to zoom, and it can be scrolled horizontally or vertically
* ☠ - skeleton key will allow any lock to be unlocked
* 🏃- run to any known room

### Map
The map shows the explored dungeon.  +/- can be used to zoom and it can be scrolled horizontally or vertically.  When the map icon is selected from the main toolbar, all rooms will be shown.

* Octogon is the starting room
* Houses are regular rooms
* Rectangles are corridor rooms
* Circles with '?' are unknown rooms
* D?? indicates a door, R?? indicates a room
* The shaded shape is the current room

The map's layout will change as it is explored.  However, the connections will remain consistent.

### Object Controls
The object controls appear in the details, doors, and monsters frames.  They will also appear in the frames for each object in another's contents.

Buttons will only appear if they're appropriate

* 🛒 - add item to player's inventory
* 🔍 - inspect further.  Perception will be asked and items revealed as necessary
* 🔨 - break item (not implemented)
* 💣 - disarm trap (not implemented)
* 💀 - monster is killed.  A monster corpse object will appear in the room's contents
* 🏃 - monster flees.  Tt will run to another room via open doors 
* 💬 - talk to monster. This should be pressed if the monster is friendly.  The monster's possessions will be revealed and the players can take items
* 🚪 - door is open or closed.  Door must be open to be used.
* 🔒 - locked or unlocked.  
* 🔏 - pick lock.  (not implemented)
* 💪 - door is stuck.  When pressed, a strength roll will be requested and if successful, the players will move to the next room.  
* 🚶 - use door.
* 🛌 - rest in room.  This is a 4-hour rest.  If wandering monsters come through during the rest, a dialog (should) appear letting them know the rest was unsuccessful.

### Details pane
This pane is the current room and it's contents

### Exits pane
This pane lists the doors that are attached to the current room.  Checkmarks appear if the door has been used previously

### Monsters pane
This pane will show any (living) monsters in the room.

### Bottom status bar
The rooms visited, the amount of XP earned, and current time in the dungeon is displayed.

## Software Requirements
This is written in Python 3.8 using the GTK3 toolkit.  Graphviz is used to generate the graph images.  I developed this on Linux, so it should run pretty much out-of-the-box there.

It should be possible to run this on Windows and MacOS with very little changes




## Todo
* Traps
* More tabular data
* Dungeon generator GUI
* Picking locks
* secret doors

## Known bugs
* Dialog when a wandering monster comes by doesn't display