"""
Contains class for minesweeper fields, which has a size attribute. The following
are equivalent: beginner/b/1/(8,8), intermediate/i/2/(16,16), expert/e/3/(16,30).
It has functions to create (manually using Tkinter or randomly) the grid of mines,
and to play the game (again using Tkinter). There are also options to have a
maximum number of mines per cell greater than 1 and to have the numbers display
the number of mines in cells adjacent by more than one cell. Function _3bv() finds
the 3bv of the grid. Threading provides the option to play while leaving the shell active.
The play() function has become a Game() class which inherits from the Minefield() class.
Changed some functions' names to ensure all are verbs.
Added menu to Tkinter window.
Added combined click action.
Added single click and drag select option.
Added change lives option.
Added highscores and settings to be stored.
Added hide timer option.
Added attribute 'game_state' in the Game play() method, which is used instead of making the grid a grid of zeros. Allows information for the end grid to be used.
Added proportion complete to show_info() for lost games and congratulations message to show_highscores() for best time.
Added zoom (Game menu).
Added distance to.

New:
Added images.

To add:
-Create all images for flags.
Improve layout and useability of custom, highscores and info.
Stop clicking clicked cells doing anything - unbind and command=None?
-Add option to double click and drag to click multiple cells and fix single drag on double left click.
Check replay(/new) action.
Improve display_grid (integrate) and add 'completed grid' option.
Add overlap layout option.
-Sort option for numbers to display distance TO a mine.
-Add option for wrap-around detection.
Add detection of 2.5.
Fix occasional crash on create new game.
Fix 'RunTimeError maximum recursion depth exceeded' error in FirstAuto.
Add third dimension.
Sort opening game on custom and saving number of mines.
Collect more information in highscores/collect statistics."""

import numpy as np
import time as tm
from Tkinter import *
from PIL import Image
import threading
from glob import glob
import os
import sys


directory = sys.path[0]
default_settings = {'per_cell': 1, 'first_success': False, 'mines': 10, 'detection': 1, 'shape': (8, 8), 'difficulty': 'b', 'lives': 1, 'drag_click': 'off', 'button_size': 16, 'distance_to': False}
settings_order = ['difficulty', 'per_cell', 'detection', 'drag_click', 'lives']
highscore_headings = ['Name', 'type', '3bv', 'other', 'Date']
detection_options = dict([(str(i), i) for i in [0.5, 1, 1.5, 1.8, 2, 2.2, 2.8, 3]])
default_mines = {(8,8):10, (16,16):40, (16,30):99, (30,16):99}
detection_mines = {
            ('b', 0.5): 10, ('b', 1): 10, ('b', 1.5): 8, ('b', 1.8): 7,
            ('b', 2): 6, ('b', 2.2): 5, ('b', 2.8): 4, ('b', 3): 4,
            ('i', 0.5): 40, ('i', 1): 40, ('i', 1.5): 30, ('i', 1.8): 25,
            ('i', 2): 25, ('i', 2.2): 20, ('i', 2.8): 16, ('i', 3): 16,
            ('e', 0.5): 99, ('e', 1): 99, ('e', 1.5): 85, ('e', 1.8): 70,
            ('e', 2): 65, ('e', 2.2): 50, ('e', 2.8): 40, ('e', 3): 40}
shape_difficulty = {(8,8):'b', (16,16):'i', (16,30):'e', (30,16):'e'}
difficulty_shape = {'b':(8,8), 'i':(16,16), 'e':(16,30)}
difficulties_list = [('b', 'Beginner'), ('i', 'Intermediate'), ('e', 'Expert'), ('c', 'Custom')]
number_colours = dict([(1,'blue'),
                (2, '#%02x%02x%02x'%(0,128,0)),
                (3, 'red'),
                (4, '#%02x%02x%02x'%(0,0,128)),
                (5, '#%02x%02x%02x'%(128,0,0)),
                (6, '#%02x%02x%02x'%(0,128,128)),
                (7, 'black'),
                (8, '#%02x%02x%02x'%(128,128,128)),
                (9, '#%02x%02x%02x'%(192,192,0)),
                (10,'#%02x%02x%02x'%(128,0,128)),
                (11,'#%02x%02x%02x'%(192,128,64)),
                (12,'#%02x%02x%02x'%(64,192,192))])
bg_colours = dict([('',   (240, 240, 237)),
                 ('red',  (255, 0, 0)),
                 ('blue', (128, 128, 255))])
cellfont = ('Times', 9, 'bold')
mineflags = ["F", "B", "C", "D", "E", "G", "H", "J", "K", "M"]
minesymbols = ['*', ':', '%', '#', '&', '$']

class Minefield(object):
    def __init__(self, shape=(16,30), per_cell=1, detection=1, distance_to=False, create='auto'):
        if type(shape) is str:
            shape = shape.lower()
        if shape in ['b', 'beginner', 1, 'easy']:
            self.shape = (8, 8)
        elif shape in ['i', 'intermediate', 2, 'medium']:
            self.shape = (16, 16)
        elif shape in ['e', 'expert', 3, 'difficult']:
            self.shape = (16, 30)
        elif type(shape) is tuple and len(shape) == 2:
            self.shape = shape
        else:
            print "Invalid shape, enter 2-tuple of integers."
            sys.exit()
        self.size = self.shape[0]*self.shape[1]
        self.per_cell = per_cell
        self.detection = detection
        self.distance_to = distance_to

        self.mines_grid = np.zeros(self.shape, int)
        self.final_grid = np.zeros(self.shape, int)
        if create == 'auto':
            self.create()
        elif create == 'manual':
            self.create_manually()

    def __str__(self):
        return ("The field has dimensions {} x {} with {n} mines and 3bv of {b}:\n".format(
                            *self.shape, n=self.mines_grid.sum(), b=self.get_3bv())
                    + prettify_grid(self.final_grid))

    def __repr__(self):
        return "<{}x{} minefield with {n} mines>".format(*self.shape, n=self.mines_grid.sum())

    def reset_button(self, button, textvar=None):
        button['image'] = button.image = ''
        button['relief'] = 'raised'
        button['fg'] = 'black'
        button['bd'] = 3
        button['bg'] = 'SystemButtonFace'
        button['font'] = self.cellfont
        if textvar:
            textvar.set("")

    def create(self, mines='default', overwrite=False, prop=None):
        #If overwrite is set to True and prop is given then prop will be used to calculate the number of mines.
        if not overwrite and self.mines_grid.any():
            print "Grid already created and overwrite is set to False."
            return
        #Only works for 2Dself.
        elif type(mines) is np.ndarray or (np.array(mines).ndim == 2 and len(mines[0] != 2)):
            self.mines_grid = mines
            self.per_cell = max(mines.max(), self.per_cell)
            self.shape = mines.shape
            self.size = mines.size
            mines = -1
        elif type(mines) in [set, list]:
            for c in list(mines):
                self.mines_grid.itemset(c, list(mines).count(c))
            self.per_cell = max(self.mines_grid.max(), self.per_cell)
        elif type(prop) in [int, float] and prop > 0 and prop < 1:
            mines = int(round(self.size*prop, 0))
        elif (mines not in range(1, self.size*self.per_cell) and self.shape in shape_difficulty and (shape_difficulty[self.shape], self.detection) in detection_mines):
            mines = detection_mines[(shape_difficulty[self.shape], self.detection)]
        elif mines not in range(1, self.size*self.per_cell):
            prop = 0.19/self.detection
            mines = int(round(float(self.size)*prop, 0))

        if mines in range(1, self.size*self.per_cell):
            if self.per_cell == 1:
                permute = np.ones(mines, int)
                permute.resize(self.size)
                self.mines_grid = np.random.permutation(permute).reshape(self.shape)
            else:
                self.mines_grid = np.zeros(self.shape, int)
                while self.mines_grid.sum() < mines:
                    cell = np.random.randint(self.size)
                    old_val = self.mines_grid.item(cell)
                    if old_val < self.per_cell:
                        self.mines_grid.itemset(cell, old_val + 1)

        self.mines = mines
        #Make a list of the coordinates of the mines.
        self.mine_coords = map(tuple, np.transpose(np.nonzero(self.mines_grid>0)))
        #Include double mines in the list twice etc.
        if self.per_cell > 1:
            repeats = []
            for c in self.mine_coords:
                if self.mines_grid[c] > 1:
                    for i in range(self.mines_grid[c] - 1):
                        repeats.append(c)
            self.mine_coords += repeats
            self.mine_coords.sort()
        self.get_final_grid()

    def create_manually(self, overwrite=False):
        if not overwrite and self.mines_grid.any():
            print "Grid already created and overwrite is set to False."
            return

        grid = -np.ones(self.shape, int)

        def quitfunc():
            self.mines_grid = np.zeros(self.shape, int)
            root.destroy()

        def clearfunc():
            self.mines_grid *= 0
            grid = -np.ones(self.shape, int)
            for b in buttons.values():
                self.reset_button(b, buttontexts[b])
                mines_var.set("000")

        def leftclick(coord):
            def action():
                b = buttons[coord]
                #Should work on the mine the mouse ends over.
                if grid[coord] >= -1:
                    b['relief'] = 'sunken'
                    b['bd'] = 0.5
                    grid[coord] += 1
                    if grid[coord] > 0:
                        buttontexts[b].set(grid[coord])
                        try:
                            b['fg'] = number_colours[grid[coord]]
                        except KeyError:
                            b['fg'] = 'black'
            return action

        def rightclick(coord):
            def action(event):
                b = buttons[coord]
                if grid[coord] == -1:
                    buttontexts[b].set("F")
                    self.mines_grid[coord] = 1
                    grid[coord] = -9
                elif grid[coord] < -1 and grid[coord] > -9*self.per_cell:
                    buttontexts[b].set(mineflags[-grid[coord]/9])
                    self.mines_grid[coord] += 1
                    grid[coord] -= 9
                else:
                    self.reset_button(b, buttontexts[b])
                    self.mines_grid[coord] = 0
                    grid[coord] = -1
                mines_var.set("%03d" % self.mines_grid.sum())
            return action

        topfont = ('Times', 10, 'bold')
        root = Tk()
        root.title("MineGauler")
        topframe = Frame(root)
        topframe.pack(side='top', pady=2)
        Button(topframe, bd=4, text="Done", font=topfont,
                  command=root.destroy).grid(row=0, column=1, padx=5)
        Button(topframe, bd=4, text="Clear", font=topfont,
                  command=clearfunc).grid(row=0, column=2, padx=5)
        Button(topframe, bd=4, text="Quit", font=topfont,
                  command=quitfunc).grid(row=0, column=3, padx=5)
        mines_var = StringVar()
        mines_var.set("000")
        Label(topframe, bd=1, fg='red', bg='black', textvariable=mines_var,
                 font=('Verdana', 12, 'bold'), padx=6).grid(row=0, column=0)

        mainframe = Frame(root)
        mainframe.pack()
        frames = make_frames_grid(mainframe, self.shape)
        buttons = dict()
        buttontexts = dict()
        for coord in sorted(list(frames)):
            btext = StringVar()
            b = Button(frames[coord], bd=2.4, takefocus=0, textvariable=btext, font=cellfont, command=leftclick(coord))
            buttons[coord] = b
            #Make the button fill the frame (stick to all sides).
            b.grid(sticky='NSEW')
            #Add the action when right click occurs.
            b.bind('<Button-3>', rightclick(coord))
            #Store the btext variable in a dictionary with the button instance as the key.
            buttontexts[b] = btext

        mainloop()

        self.mine_coords = map(tuple, np.transpose(np.nonzero(self.mines_grid>0)))
        self.get_final_grid()
        self.get_openings()
        ##DispThread(threading.active_count(), self, (self.final_grid,)).start()
        prettify_grid(self.final_grid, 1)

    def get_final_grid(self):
        self.final_grid = -9 * self.mines_grid
        if self.distance_to:
            for coord in np.transpose(np.nonzero(self.mines_grid==0)):
                detection = 0.5 if self.detection == 0.5 else 1
                while True:
                    adjacent = sum(map(lambda k: self.mines_grid[k], self.get_neighbours(tuple(coord), detection)))
                    if adjacent:
                        self.final_grid.itemset(tuple(coord), int(detection+0.999) - adjacent)
                        break
                    detection += 1
        else:
            for coord in np.transpose(np.nonzero(self.mines_grid==0)):
                self.final_grid.itemset(tuple(coord), sum(map(lambda k: self.mines_grid[k], self.get_neighbours(tuple(coord), self.detection))))
        patches = self.get_openings()
        return self.final_grid

    def get_neighbours(self, coord, dist=1, include=False):
        d = int(dist) if dist % 1 == 0 else int(dist) + 1
        i, j = coord
        x, y = self.shape
        row = [u for u in range(i-d, i+1+d) if u in range(x)]
        col = [v for v in range(j-d, j+1+d) if v in range(y)]
        if dist % 1 > 0.5:
            neighbours = {(u, v) for u in row for v in col
                          if abs(u-i) + abs(v-j) < 2*d}
        elif dist % 1 != 0:
            neighbours = {(u, v) for u in row for v in col
                          if abs(u-i) + abs(v-j) <= d}
        else:
            neighbours = {(u, v) for u in row for v in col}
        if not include:
            ##The given coord is not included.
            neighbours.remove(coord)
        return neighbours

    def get_openings(self):
        if self.distance_to:
            opening_coords = set(map(tuple, np.transpose(np.nonzero(self.final_grid>0))))
        else:
            opening_coords = set(map(tuple, np.transpose(np.nonzero(self.final_grid==0))))
        if self.distance_to:
            detection = 0.5 if self.detection == 0.5 else 1
            check = set()
            found_coords = set()
            patches = []
            while len(opening_coords.difference(found_coords)) > 0:
                cur_patch = set()
                check.add(list(opening_coords.difference(found_coords))[0])
                while len(check) > 0:
                    found_coords.update(check) #Same as |= (below)
                    coord = check.pop()
                    cur_patch.add(coord)
                    cur_patch |= self.get_neighbours(coord, detection)
                    check |= self.get_neighbours(coord, detection) & (opening_coords - found_coords)
                patches.append(cur_patch)
            self.openings = patches
        else:
            check = set()
            found_coords = set()
            patches = []
            while len(opening_coords.difference(found_coords)) > 0:
                cur_patch = set()
                check.add(list(opening_coords.difference(found_coords))[0])
                while len(check) > 0:
                    found_coords.update(check) #Same as |= (below)
                    coord = check.pop()
                    cur_patch.add(coord)
                    cur_patch |= self.get_neighbours(coord, self.detection)
                    check |= self.get_neighbours(coord, self.detection) & (opening_coords - found_coords)
                patches.append(cur_patch)
            self.openings = patches
        return self.openings

    def get_3bv(self):
        clicks = len(self.get_openings())
        exposed = len({c for patch in self.openings for c in patch})
        clicks += self.size - len(set(self.mine_coords)) - exposed
        return clicks


class Game(Minefield):
    def __init__(self, play=True):
        try:
            with open(directory + r'\Settings.txt', 'r') as f:
                settings = eval(f.read())
        except:
            settings = default_settings
        # print "Imported settings: ", settings
        for s in settings:
            setattr(self, s, settings[s])
        self.visitor = False
        self.distance_to = False
        #self.settings = {'per_cell': self.per_cell, 'first_success': self.first_success, 'mines': self.mines, 'detection': self.detection, 'shape': self.shape, 'difficulty': self.difficulty, 'lives': self.lives, 'drag_click': self.drag_click, 'visitor': self.visitor, 'button_size': self.button_size, 'distance_to': self.distance_to}
        self.cellfont = ('Tahoma', (10*self.button_size)/17, 'bold')
        #Necessary??
        if self.difficulty != 'c':
            shape = self.difficulty
        else:
            shape = self.shape
        super(Game, self).__init__(shape, per_cell=self.per_cell, detection=self.detection, distance_to=self.distance_to)

        self.highscores = dict()
        try:
            for d in ['Beginner', 'Intermediate', 'Expert']:
                with open(directory + '\\' + d + r'\highscores6.txt', 'r') as f:
                    self.highscores.update(eval(f.read()))
        except:
            pass #Will be created when needed.

        if play:
            self.play(self.mines)

    def __str__(self):
        return ("This {} x {} game has {n} mines and 3bv of {b}:\n".format(*self.shape, n=self.mines, b=self.get_3bv()) + prettify_grid(self.final_grid))

    def __repr__(self):
        return "<{}x{} MineGauler game with {n} mines>".format(*self.shape, n=self.mines_grid.sum())

    def thread_play(self, mines='default'):
        ##Only works once per running...?
        PlayThread(threading.active_count(), self, (mines,)).start()
        tm.sleep(2)
        print ">>> ",

    def play(self, mines='default', first_success=False):
        self.grid = -np.ones(self.shape, int)
        self.time_passed = None
        self.leftbuttondown, self.rightbuttondown = False, False
        self.coord_leftclicked, self.coord_rightclicked = None, None
        self.original_coord, self.coord_flagged = None, None
        self.blockclick, self.score_checked = False, False
        self.game_origin = None
        self.game_state = 'ready'
        self.game_zoom = round(100*self.button_size/16.0, 0)

        def get_images():
            im_size = self.button_size - 6
            im_path = directory + '\\Images\\Mines\\'
            #Image() is from PIL, used to convert/resize/recolour the image.
            for n in [i for i in range(1, 11) if not os.path.isfile(im_path + str(i) + 'mine' + str(im_size) + '.ppm')]:
                for colour in bg_colours:
                    im = Image.open(im_path + str(n) + 'mine.png')
                    data = np.array(im)
                    data[(data == (255, 255, 255, 0)).all(axis=-1)] = tuple(list(bg_colours[colour]) + [0])
                    im = Image.fromarray(data, mode='RGBA').convert('RGB')
                    im = im.resize(tuple([im_size]*2), Image.ANTIALIAS)
                    im.save(im_path + colour + str(n) + 'mine' + str(im_size) + '.ppm')
                    im.close()
            im_path = directory + '\\Images\\Flags\\'
            for n in [i for i in range(1, 3) if not os.path.isfile(im_path + str(i) + 'flag' + str(im_size) + '.ppm')]:
                im = Image.open(im_path + str(n) + 'flag.png')
                data = np.array(im)
                data[(data == (255, 255, 255, 0)).all(axis=-1)] = tuple(list(bg_colours['']) + [0])
                im = Image.fromarray(data, mode='RGBA').convert('RGB')
                im = im.resize(tuple([im_size]*2), Image.ANTIALIAS)
                im.save(im_path + '%sflag%02d'%(n, im_size) + '.ppm')
                im.close()
        get_images()


        def click(coord):
            b = self.buttons[coord]
            b['relief'] = 'sunken'
            b['bd'] = 0.5
            if self.final_grid[coord] != 0:
                try:
                    b['fg'] = number_colours[self.final_grid[coord]]
                except KeyError:
                    b['fg'] = 'black'
                buttontexts[b].set(self.final_grid[coord])
            self.grid.itemset(coord, self.final_grid[coord])

        def new(reset=True):
            if create_var.get():
                create_game(reset)
                return
            self.game_state = 'ready'
            self.game_origin = None
            self.score_checked = False
            if per_cell_var.get() > 0:
                self.per_cell = per_cell_var.get()
            self.detection = detection_options[detection_var.get()]
            #If detection changes and difficulty was on a default, change the number of mines as appropriate.
            if self.difficulty != 'c':
                self.mines = detection_mines[(self.difficulty, self.detection)]
            self.create(self.mines, overwrite=1)
            replay(reset, new=True)

        def create_game(reset=True):
            #Only implement if create_var is true.
            if create_var.get():
                self.game_state = 'create'
                self.mines_grid = np.zeros(self.shape, int)
                self.mine_coords = []
                self.mines = 0
                if reset:
                    for coord in self.buttons:
                        self.reset_button(self.buttons[coord], buttontexts[self.buttons[coord]])
                self.grid = -np.ones(self.shape, int)
                self.start = 0
                timer_var.set("000")
                mines_var.set("%03d" % self.mines_grid.sum())
                if per_cell_var.get() > 0:
                    self.per_cell = per_cell_var.get()
                self.detection = detection_options[detection_var.get()]
                new_button_frame.forget()
                timer_label.forget()
                done_button.pack(side='left')
                first_success_var.set(False)
            else:
                self.create(self.mines, overwrite=1)
                self.game_origin = None
                self.game_state = 'ready'
                replay(new=True)
                done_button.forget()
                new_button_frame.pack(side='left')
                timer_label.pack(side='left')

        def show_info():
            try:
                if self.focus.bindtags()[1] == 'Entry' or self.focus.title() == 'Info':
                    self.focus.focus_set()
                    return
            except TclError:
                #self.focus has been destroyed.
                pass
            if not self.start:
                if per_cell_var.get() > 0:
                    self.per_cell = per_cell_var.get()
                self.first_success = first_success_var.get()
                self.detection = detection_options[detection_var.get()]
            self.focus = info_window = Toplevel(root)
            info_window.title('Info')
            if create_var.get():
                #Improve this.
                self.detection = float(detection_var.get())
                created_minefield = Minefield(self.shape, self.per_cell, self.detection, create=False)
                created_minefield.mines_grid = np.where(self.grid<-1, -self.grid/9, 0)
                created_minefield.mine_coords = set(map(tuple, np.transpose(np.nonzero(self.mines_grid>0))))
                created_minefield.get_final_grid()
                m = created_minefield
            else:
                m = self
            info = "This {} x {} grid has {n} mines with a max of {p} per cell.\nDetection level: {d}, Drag click: {c}, Lives remaining: {l}".format(*self.shape, p=self.per_cell, n=m.mines_grid.sum(), d=self.detection, c=self.drag_click, l=lives_remaining_var.get())
            if self.game_state in ['won', 'lost']:
                info += "\n\nIt has 3bv of {b}.".format(b=m.get_3bv())
            if self.game_state == 'won':
                info += "\n\nYou completed it in {:.2f} seconds, with 3bv/s of {:.2f}.".format(self.time_passed+0.005, self.get_3bv()/self.time_passed+0.005)
            elif self.game_state == 'lost':
                lost_field = Minefield(shape=self.shape, detection=self.detection, create=False)
                lost_field.mine_coords = set(map(tuple, np.transpose(np.nonzero(self.mines_grid>0))))
                lost_field.final_grid = np.where(self.grid < 0, self.final_grid, 1)
                rem_3bv = lost_field.get_3bv()
                already_found = {c for c in set(map(tuple, np.transpose(np.nonzero(self.grid >= 0)))) if c not in [i for p in lost_field.openings for i in p]}
                rem_3bv -= len(already_found)
                prop_complete = float(self.get_3bv()-rem_3bv)/self.get_3bv()
                info += "\n\nYou lost in {:.2f} seconds, completing {:.1f}%. The grid\nhas remaining 3bv of {} with predicted completion time\nof {:.1f} seconds with a continued 3bv/s of {:.2f}.".format(self.time_passed+0.005, 100*prop_complete, rem_3bv, self.time_passed/prop_complete, prop_complete*self.get_3bv()/self.time_passed)
            Label(info_window, text=info, font=('Times', 10, 'bold')).pack()

        def show_highscores(settings=None, flagging=None, htype='Time', window=None):
            try:
                if self.focus.bindtags()[1] == 'Entry':
                    self.focus.focus_set()
                    return
            except TclError:
                pass
            if not settings:
                if not self.start:
                    if per_cell_var.get() > 0:
                        self.per_cell = per_cell_var.get()
                    self.first_success = first_success_var.get()
                    self.detection = detection_options[detection_var.get()]
                if self.difficulty == 'c' or self.lives > 3:
                    return
                settings = []
                for s in settings_order:
                    settings.append(getattr(self, s))
                settings = tuple(settings)

            if not window:
                self.focus = window = Toplevel(root)
                window.title('Highscores')
                #window.resizable(False, False)
            else:
                self.focus = window

            headings = highscore_headings
            headings[1] = htype
            headings[3] = '3bv/s' if headings[1] != '3bv/s' else 'Time'
            #Funny business.
            if self.lives > 1 and 'Lives remaining' not in headings:
                headings.insert(-1, 'Lives remaining')
            elif self.lives == 1 and 'Lives remaining' in headings:
                headings.remove('Lives remaining')

            diff = dict(difficulties_list)[settings[0]].lower()
            flag = 'non-flagged ' if flagging == 'NF' else ('flagged ' if flagging == 'F' else '')
            lives = ', Lives = %s\n' % self.lives if self.lives > 1 else '\n'
            intro = "{t} highscores for {f}{d} with:\nMax per cell = {1}, Detection = {2}, Drag = {3}{L}".format(*settings, t=htype, d=diff, f=flag, L=lives)
            Label(window, text=intro, font=('times', 12, 'normal')).grid(row=1, column=0, columnspan=len(headings)+1)
            for i in headings:
                Label(window, text='Lives left' if i == 'Lives remaining' else i).grid(row=2, column=headings.index(i)+1)

            highscores = [] if settings not in self.highscores else sorted([d for d in self.highscores[settings] if not flagging or d['Flagging'] == flagging], key=lambda d: float(d[htype]), reverse=True if htype =='3bv/s' else False)
            if settings in self.highscores and self.highscores[settings][-1]['Mine coords'] == self.mine_coords:
                current = self.highscores[settings][-1]
            else:
                current = None
            if self.visitor:
                highscores = reduce(lambda x, y: x + ([y] if (y['Name'] or y==current) and y['Name'] not in map(lambda d: d['Name'], x) else []), highscores, [])


            if current and htype == 'Time' and not flagging and settings[-1] == 1 and self.highscores[settings][-1] == min(self.highscores[settings], key=lambda d: float(d['Time'])):
                Label(window, padx=10, pady=10, bg='yellow', text="Congratulations, you set a new\nall-time MineGauler time record\nfor these settings!!", font=('Times', 12, 'bold')).grid(row=0, columnspan=len(headings)+1)
            def set_name(event):
                name = event.widget.get()
                self.highscores[settings][-1]['Name'] = name
                row = event.widget.grid_info()['row']
                event.widget.destroy()
                Label(window, text=name, font=('times', 9, 'bold')).grid(row=row, column=1)
                self.focus = window
                #Do not overwrite the main file until data is stored in other file.
                with open(directory + '\\' + dict(difficulties_list)[self.difficulty] + r'\highscores6.txt', 'r') as f:
                    old_highscores = f.read()
                with open(directory + '\\' + dict(difficulties_list)[self.difficulty] + r'\highscorescopy.txt', 'w') as f:
                    f.write(old_highscores)
                with open(directory + '\\' + dict(difficulties_list)[self.difficulty] + r'\highscores6.txt', 'w') as f:
                    f.write(str(dict([(k, v) for (k, v) in self.highscores.items() if k[0] == self.difficulty])))
                for w in window.children.values():
                    w.destroy()
                show_highscores(settings, flagging, htype, window)
            row = 3
            for d in highscores:
                font = ('Times', 10, 'bold') if d['Mine coords'] == self.mine_coords else ('Times', 10, 'normal')
                Label(window, text=row-2, font=font).grid(row=row, column=0)
                col = 1
                for i in headings:
                    if i == 'Name' and not d[i] and d['Mine coords'] == self.mine_coords:
                        self.focus = e = Entry(window)
                        e.grid(row=row, column=col)
                        e.bind('<Return>', set_name)
                    else:
                        Label(window, text=d[i], font=font).grid(row=row, column=col)
                    col += 1
                row += 1
                if row == 13:
                    break

            lower_frame = Frame(window)
            lower_frame.grid(row=14, column=0, columnspan=len(headings)+1)
            def change_flagging():
                for w in window.children.values():
                    w.destroy()
                flagging = None if flagging_var.get() == 'None' else flagging_var.get()
                show_highscores(settings, flagging, htype, window)
            flagging_var = StringVar()
            flagging_var.set(str(flagging))
            for i in [('All', 'None'), ('Flagged', 'F'), ('Non-flagged', 'NF')]:
                Radiobutton(lower_frame, text=i[0], font=('times', 10, 'bold'), value=i[1], variable=flagging_var, command=change_flagging).pack(side='left')
            def change_type():
                ####Add in self.visitor=True action.
                for w in window.children.values():
                    w.destroy()
                    t = 'Time' if htype == '3bv/s' else '3bv/s'
                show_highscores(settings, flagging, htype=t, window=window)
            Button(lower_frame, padx=10, bd=3, text='Time / 3bv/s', font=('times', 10, 'bold'), command=change_type).pack(side='top')
            self.focus.focus_set()

        def done_action():
            "Only used when creating game."
            create_var.set('False')
            self.game_origin = 'created'
            self.mines_grid = np.where(self.grid < -1, -self.grid/9, 0)
            self.mine_coords = map(tuple, np.transpose(np.nonzero(self.mines_grid>0)))
            self.mines = self.mines_grid.sum()
            self.get_final_grid()
            self.get_openings()
            ##DispThread(threading.active_count(), self, (self.final_grid,)).start()
            prettify_grid(self.final_grid, 1)
            replay()
            done_button.forget()
            new_button_frame.pack(side='left')
            timer_label.pack(side='left')
            first_success_var.set(False)
            diff = shape_difficulty[self.shape] if self.shape in shape_difficulty else 'c'
            if diff != 'c' and detection_mines[(diff, self.detection)] == self.mines:
                self.difficulty = diff
                difficulty_var.set(diff)

        def replay(reset=True, new=False):
            if not new:
                self.game_state = 'ready'
                self.game_origin = 'replay'
            set_detection()
            set_distance_to()
            set_drag()
            self.game_zoom = round(100*self.button_size/16.0, 0)
            if reset:
                for coord in self.buttons:
                 self.reset_button(self.buttons[coord], buttontexts[self.buttons[coord]])
            self.grid = -np.ones(self.shape, int)
            self.time_passed = None
            #Needed when a game is stopped to restart/new....?
            self.start = 0
            timer_var.set("000")
            n = self.lives
            face_button['image'] = self.face_images['ready%sface'%n]
            if timer_hide_var.get():
                timer_label['fg'] = 'black'
            mines_var.set("%03d" % self.mines_grid.sum())
            mines_label.config(bg='black', fg='red')
            lives_remaining_var.set(self.lives)

        def change_shape():
            self.start = 0
            #To avoid problems with grid size in replay(), reset the self.buttons here.
            new()
            def reshape():
                #This runs if one of the dimensions of the previous shape was larger.
                for coord in [(u, v) for u in range(self.grid.shape[0]) for v in range(self.grid.shape[1]) if u >= self.shape[0] or v >= self.shape[1]]:
                    #Could use mainframe.children rather than having frames global.
                    frames[coord].grid_forget()
                    self.buttons.pop(coord)
                #This runs if one of the dimensions of the new shape is larger than the previous.
                for coord in [(u, v) for u in range(self.shape[0]) for v in range(self.shape[1]) if u >= self.grid.shape[0] or v >= self.grid.shape[1]]:
                    if coord in frames:
                        frames[coord].grid_propagate(False)
                        frames[coord].grid(row=coord[0], column=coord[1])
                        self.buttons[coord] = frames[coord].children.values()[0]
                    else:
                        make_button(coord)
                new(reset=False)
                tm.sleep(0.5)

            def get_shape(event):
                self.shape = (rows.get(), cols.get())
                self.size = self.shape[0] * self.shape[1]
                self.mines = mines.get()
                if self.mines < 1:
                    self.mines = int(round(float(self.size)*0.19/self.detection, 0))
                #Check if this is actually custom.
                diff = shape_difficulty[self.shape] if self.shape in shape_difficulty else 'c'
                if diff != 'c' and detection_mines[(diff, self.detection)] == self.mines:
                    self.difficulty = diff
                    difficulty_var.set(diff)
                else:
                    self.difficulty = 'c'
                    difficulty_var.set('c')
                reshape()
                customise_window.destroy()

            if difficulty_var.get() == 'c':
                difficulty_var.set(self.difficulty)
                try:
                    if self.focus.bindtags()[1] == 'Entry':
                        self.focus.focus_set()
                        return
                except TclError:
                    pass
                def get_mines(event):
                    shape = (rows.get(), cols.get())
                    if shape in shape_difficulty:
                        mines.set(detection_mines[(shape_difficulty[shape], self.detection)])
                    else:
                        #Formula for getting reasonable number of mines.
                        d = float(detection_var.get()) - 1
                        mines.set(int((0.09*d**3 - 0.25*d**2 - 0.15*d + 1)*(shape[0]*shape[1]*0.2)))
                customise_window = Toplevel(root)
                customise_window.title('Custom')
                Label(customise_window, text="Enter a number for each\nof the following then press enter.").grid(row=0, column=0, columnspan=2)
                rows = IntVar()
                rows.set(self.shape[0])
                cols = IntVar()
                cols.set(self.shape[1])
                mines = IntVar()
                mines.set(self.mines)
                self.focus = rows_entry = Entry(customise_window, textvariable=rows)
                rows_entry.icursor(END)
                columns_entry = Entry(customise_window, textvariable=cols)
                mines_entry = Entry(customise_window, textvariable=mines)
                Label(customise_window, text='Rows').grid(row=1, column=0)
                rows_entry.grid(row=1, column=1)
                Label(customise_window, text='Columns').grid(row=2, column=0)
                columns_entry.grid(row=2, column=1)
                Label(customise_window, text='Mines').grid(row=3, column=0)
                mines_entry.grid(row=3, column=1)
                rows_entry.bind('<FocusOut>', get_mines)
                columns_entry.bind('<FocusOut>', get_mines)
                rows_entry.bind('<Return>', get_shape)
                columns_entry.bind('<Return>', get_shape)
                mines_entry.bind('<Return>', get_shape)
                rows_entry.focus_set()
            else:
                self.difficulty = difficulty_var.get()
                self.shape = difficulty_shape[self.difficulty]
                self.size = self.shape[0] * self.shape[1]
                self.mines = detection_mines[(self.difficulty, self.detection)]
                reshape()

        def set_zoom():
            try:
                if self.focus.bindtags()[1] == 'Entry':
                    self.focus.focus_set()
                    return
            except TclError:
                pass
            def get_zoom(event=None):
                old_button_size = self.button_size
                if event:
                    self.button_size = max(10, min(100, int(event.widget.get())))
                else:
                    self.button_size = 16
                if self.game_state == 'active':
                    self.game_zoom = 'variable'
                else:
                    self.game_zoom = round(100*self.button_size/16.0, 0)
                if self.button_size == 16:
                    zoom_var.set(False)
                else:
                    zoom_var.set(True)
                if old_button_size != self.button_size:
                    self.cellfont = (self.cellfont[0], (10*self.button_size)/17, self.cellfont[2])
                    for f in frames.values():
                        f.config(height=self.button_size, width=self.button_size)
                        f.children.values()[0]['font'] = self.cellfont
                    get_images()
                    #This could be written better!
                    im_path = directory + '\\Images\\Mines\\'
                    im_size = self.button_size - 6
                    mine_image = PhotoImage(name='1mine%02d'%im_size, file=im_path + '1mine%02d'%im_size + '.ppm')
                    for b in [b1 for b1 in self.buttons.values() if b1['image'] and 'mine' in b1.image.name]:
                        im_name = '{}{:02d}'.format(b.image.name[:-2], im_size)
                        if im_name[:-2] == '1mine':
                            b['image'] = b.image = mine_image
                        else:
                            b['image'] = b.image = PhotoImage(name=im_name, file=im_path + im_name + '.ppm')
                    for n in self.flag_images:
                        im_name = '%sflag%02d' % (n, im_size)
                        self.flag_images[n] = PhotoImage(name=im_name, file=directory + '\\Images\\Flags\\' + im_name + '.ppm')
                    for b in [b1 for b1 in self.buttons.values() if b1['image'] and 'flag' in b1.image.name]:
                        im_name = '{}{:02d}'.format(b.image.name[:-2], im_size)
                        b['image'] = b.image = self.flag_images[int(im_name[0])]
                window.destroy()
            window = Toplevel(root)
            window.title('Zoom')
            Message(window, width=150, text="Enter desired button size in pixels or click 'Default'.").pack()
            self.focus = zoom_entry = Entry(window, width=5)
            zoom_entry.insert(0, self.button_size)
            zoom_entry.pack(side='left', padx=30)
            zoom_entry.bind('<Return>', get_zoom)
            zoom_entry.focus_set()
            Button(window, text='Default', command=get_zoom).pack(side='left')

        def toggle_timer():
            if timer_hide_var.get() and self.game_state in ['ready', 'active']:
                timer_label['fg'] = 'black'
            else:
                timer_label['fg'] = 'red'

        def reset_settings():
            for s in default_settings:
                setattr(self, s, default_settings[s])
            first_success_var.set(self.first_success)
            if self.lives > 1:
                lives_var.set(True)
            else:
                lives_var.set(False)
            drag_click_var.set(self.drag_click)
            if self.per_cell in [1, 2, 10]:
                per_cell_var.set(self.per_cell)
            else:
                per_cell_var.set(-1)
            difficulty_var.set(self.difficulty)
            detection_var.set(self.detection)
            visitor_var.set(self.visitor)
            self.zoom = 1
            for f in frames.values():
                f.config(height=16, width=16)
            change_shape()

        def choose_lives():
            if self.lives > 1:
                lives_var.set(True)
            else:
                lives_var.set(False)
            if self.game_state == 'active':
                return
            try:
                if self.focus.bindtags()[1] == 'Entry':
                    self.focus.focus_set()
                    return
            except TclError:
                pass
            def get_lives(event):
                try:
                    self.lives = max(1, int(event.widget.get()))
                except ValueError:
                    self.lives = 1
                lives_remaining_var.set(self.lives)
                if self.lives > 1:
                    lives_var.set(True)
                else:
                    lives_var.set(False)
                lives_window.destroy()
                n = min(3, lives_remaining_var.get())
                face_button['image'] = self.face_images['ready%sface'%n]

            lives_window = Toplevel(root)
            lives_window.title('Lives')
            Message(lives_window, text="Enter a number of lives.").pack()
            self.focus = lives_entry = Entry(lives_window)
            lives_entry.insert(0, self.lives)
            lives_entry.pack()
            lives_entry.bind('<Return>', get_lives)
            lives_entry.focus_set()


        self.focus = root = Tk()
        root.title('MineGauler0.0.8')
        #Turns off the option to resize the window.
        root.resizable(False, False)

        im_size = self.button_size - 6
        self.mine_image = PhotoImage(name='1mine', file=directory + '\\Images\\Mines\\1mine' + str(im_size) + '.ppm')
        self.flag_images = dict()
        for n in range(1, 3):
            im_name = '%sflag%02d' % (n, im_size)
            self.flag_images[n] = PhotoImage(name=im_name, file=directory + '\\Images\\Flags\\' + im_name + '.ppm')

        self.face_images = dict()
        for path in glob(directory + '\\Images\\Faces\\*.ppm'):
            im_name = path.split('\\')[-1][:-4]
            self.face_images[im_name] = PhotoImage(name=im_name, file=directory + '\\Images\\Faces\\' + im_name + '.ppm')

        menubar = Menu(root)
        root.config(menu=menubar)
        root.option_add('*tearOff', False)
        game_menu = Menu(menubar)
        menubar.add_cascade(label='Game', menu=game_menu)

        game_menu.add_command(label='New', command=new)
        game_menu.add_command(label='Replay', command=replay)
        create_var = BooleanVar()
        game_menu.add_checkbutton(label='Create', variable=create_var, command=create_game)
        game_menu.add_command(label='Current info', command=show_info)
        game_menu.add_command(label='Highscores', command=show_highscores)
        game_menu.add_command(label='Statistics', command=None, state='disabled')

        game_menu.add_separator()
        difficulty_var = StringVar()
        difficulty_var.set(self.difficulty)
        for i in difficulties_list:
            game_menu.add_radiobutton(label=i[1], value=i[0], variable=difficulty_var, command=change_shape)

        game_menu.add_separator()
        zoom_var = BooleanVar()
        if self.button_size != 16:
            zoom_var.set(True)
        game_menu.add_checkbutton(label='Zoom', variable=zoom_var, command=set_zoom)
        timer_hide_var = BooleanVar()
        timer_hide_var.set(False)
        game_menu.add_checkbutton(label='Hide timer', variable=timer_hide_var, command=toggle_timer)
        visitor_var = BooleanVar()
        game_menu.add_checkbutton(label='Visitor', variable=visitor_var, command=lambda: setattr(self,'visitor', visitor_var.get()))
        game_menu.add_command(label='Reset to default', command=reset_settings)

        game_menu.add_separator()
        game_menu.add_command(label='Exit', command=root.destroy)


        options_menu = Menu(menubar)
        menubar.add_cascade(label='Options', menu=options_menu)

        first_success_var = BooleanVar()
        first_success_var.set(self.first_success)
        options_menu.add_checkbutton(label='FirstAuto', variable=first_success_var, command=setattr(self, 'first_success', first_success_var.get()))

        #Used on the new game button as textvariable.
        lives_remaining_var = IntVar()
        lives_remaining_var.set(self.lives)
        lives_var = BooleanVar()
        if self.lives > 1:
            lives_var.set(True)
        options_menu.add_checkbutton(label='Lives', variable=lives_var, command=choose_lives)

        per_cell_menu = Menu(options_menu)
        per_cell_var = IntVar()
        per_cell_var.set(-1 if self.per_cell not in [1, 2, 10] else self.per_cell)
        options_menu.add_cascade(label='Max mines per cell', menu=per_cell_menu)
        per_cell_menu.add_radiobutton(label='1', value=1, variable=per_cell_var)
        per_cell_menu.add_radiobutton(label='2', value=2, variable=per_cell_var)
        per_cell_menu.add_radiobutton(label='Many', value=10, variable=per_cell_var)
        per_cell_menu.add_radiobutton(label='(Other)', value=-1, variable=per_cell_var, state='disabled')

        def set_detection():
            if self.game_state != 'active':
                self.detection = detection_options[detection_var.get()]
                self.get_final_grid()
        detection_menu = Menu(options_menu)
        detection_var = StringVar()
        detection_var.set(self.detection)
        options_menu.add_cascade(label='Detection strength', menu=detection_menu)
        #Add detection options.
        for i in sorted(list(detection_options)):
            detection_menu.add_radiobutton(label=i, value=i, variable=detection_var, command=set_detection)

        def set_drag():
            if self.game_state != 'active':
                self.drag_click = drag_click_var.get()
        dragclick_menu = Menu(options_menu)
        options_menu.add_cascade(label='Drag and select', menu=dragclick_menu)
        drag_click_var = StringVar()
        drag_click_var.set(self.drag_click)
        for i in ['Off', 'Single click', 'Double click']:
            #Double click not yet working.
            if i[0] == 'D':
                state = 'disabled'
            else:
                state = 'active'
            dragclick_menu.add_radiobutton(label=i, value=i.split()[0].lower(), variable=drag_click_var, command=set_drag, state=state)

        options_menu.add_separator()
        def set_distance_to():
            for i in range(2, len(detection_options)):
                detection_menu.entryconfig(i, state = 'disabled' if distance_to_var.get() else 'normal')
            if self.game_state != 'active':
                self.distance_to = distance_to_var.get()
                self.get_final_grid()
        distance_to_var = BooleanVar()
        options_menu.add_checkbutton(label='Distance to', variable=distance_to_var, command=set_distance_to)


        help_menu = Menu(menubar)
        menubar.add_cascade(label='Help', menu=help_menu)
        help_menu.add_command(label='Basic rules', command=None, state='disabled')
        help_menu.add_command(label='Additional features', command=lambda: os.startfile(directory + '\\Features.txt'))
        help_menu.add_separator()
        help_menu.add_command(label='About', command=None, state='disabled')


        topframe = Frame(root, pady=2)
        topframe.pack()
        mines_var = StringVar()
        mines_var.set("%03d" % self.mines_grid.sum())
        mines_label = Label(topframe, padx=5, bg='black', fg='red', bd=5, relief='sunken', font=('Verdana',11,'bold'), textvariable=mines_var)
        mines_label.pack(side='left')
        new_button_frame = Frame(topframe, padx=6, width=40, height=25)
        new_button_frame.pack(side='left')
        n = min(self.lives, 3)
        face_button = Button(new_button_frame, bd=2, image=self.face_images['ready%sface'%n], command=new)
        face_button.grid(sticky='nsew')
        timer_var = StringVar()
        timer_var.set("000")
        timer_label = Label(topframe, padx=5, bg='black', fg='red', bd=5, relief='sunken', font=('Verdana',11,'bold'), textvariable=timer_var)
        timer_label.pack(side='left')
        done_button = Button(topframe, padx=10, bd=4, text="Done", font=('Times', 10, 'bold'), command=done_action)

        def set_highscore(htype='Time'):
            self.score_checked = True
            if self.difficulty == 'c' or self.game_origin or self.lives > 3 or self.time_passed < 0.5:
                return
            flagging = 'F' if np.where((self.grid % 9 == 0) * (self.grid < 0), 1, 0).sum() > self.lives - lives_remaining_var.get() else 'NF'
            entry = {
                'Name': "",
                'Time': "{:.2f}".format(self.time_passed+0.005),
                '3bv': self.get_3bv(),
                '3bv/s': "{:.2f}".format(self.get_3bv()/self.time_passed+0.005),
                'Flagging': flagging,
                'Date': tm.strftime('%d %b %Y %X', tm.localtime()),
                'Lives remaining': lives_remaining_var.get(),
                'First success': self.first_success,
                'Mine coords': self.mine_coords,
                'Zoom': self.game_zoom}
            settings = []
            for s in settings_order:
                settings.append(getattr(self, s))
            settings = tuple(settings)
            if settings not in self.highscores:
                self.highscores[settings] = []
            if len(self.highscores[settings]) < 10 or self.visitor or float(entry['Time']) < sorted(map(lambda d: float(d['Time']), self.highscores[settings]))[9]:
                self.highscores[settings].append(entry)
                show_highscores(settings)
            elif float(entry['3bv/s']) > sorted(map(lambda d: float(d['3bv/s']), self.highscores[settings]), reverse=True)[9]:
                self.highscores[settings].append(entry)
                show_highscores(settings, htype='3bv/s')
            elif len([d for d in self.highscores[settings] if d['Flagging'] == flagging]) < 10 or float(entry['Time']) < sorted(map(lambda d: float(d['Time']), [d for d in self.highscores[settings] if d['Flagging'] == flagging]))[9]:
                self.highscores[settings].append(entry)
                show_highscores(settings, flagging)
            elif  float(entry['3bv/s']) > sorted(map(lambda d: float(d['3bv/s']), [d for d in self.highscores[settings] if d['Flagging'] == flagging]), reverse=True)[9]:
                self.highscores[settings].append(entry)
                show_highscores(settings, flagging, htype='3bv/s')

        def leftclick(coord=None, actual_click=True):
            if not coord:
                coord = self.coord_leftclicked
            elif coord == self.coord_leftclicked:
                actual_click = True
            b = self.buttons[coord]
            if actual_click:
                self.leftbuttondown = False
                if self.rightbuttondown:
                    if create_var.get():
                        self.blockclick = True
                    combinedclick(self.coord_rightclicked)
                    return
                elif self.drag_click == 'single' and self.final_grid[coord] >= 0 and self.grid[coord] >= -1 and self.game_state in ['active', 'won']:
                    # b['relief'] == 'sunken' #Why is this not sufficient?!!
                    click(coord)
                    return
                #Used in doubleleftclick().
                elif self.blockclick:
                    self.blockclick = False
                    return
            #Return out of the function if a window with an Entry widget is open.
            try:
                if self.focus.bindtags()[1] == 'Entry':
                    self.focus.focus_set()
                    return
            except TclError:
                pass
            if create_var.get() and self.grid[coord] >= -1:
                b.config(relief='sunken', bd=0.5)
                self.grid[coord] += 1
                if self.grid[coord] > 0:
                    buttontexts[b].set(self.grid[coord])
                    try:
                        b['fg'] = number_colours[self.grid[coord]]
                    except KeyError:
                        b['fg'] = 'black'
            else:
                #If game hasn't been started.
                if self.game_state == 'ready':
                    if per_cell_var.get() not in [self.per_cell, -1] and not self.game_origin:
                        self.per_cell = per_cell_var.get()
                        self.create(self.mines, overwrite=1)
                        b.invoke()
                        return
                    if first_success_var.get() and not self.game_origin and ((self.final_grid[coord] != 0 and not self.distance_to) or (self.final_grid[coord] < 1 and self.distance_to)): #First success criteria.
                        if self.difficulty != 'c' or not self.final_grid.all():
                            self.create(self.mines_grid.sum(), overwrite=1)
                            b.invoke()
                            return
                        else:
                            print "Unable to find zero patch - change the settings."
                    self.start = tm.time()
                    timer_var.set("001")
                    self.mines = self.mines_grid.sum()
                    self.game_state = 'active'
                if self.grid[coord] == -1 and self.game_state in ['ready', 'active']:
                    #If an opening is clicked.
                    if (self.distance_to and self.final_grid[coord] > 0) or (not self.distance_to and self.final_grid[coord] == 0):
                        for patch in self.openings:
                            if coord in patch:
                                break
                        for c in patch:
                            if self.grid[c] == -1:
                                click(c)
                    #If a safe button is clicked.
                    elif (self.distance_to and self.final_grid[coord] > -9) or (not self.distance_to and self.final_grid[coord] > 0):
                        click(coord)
                    #Otherwise a mine is hit.
                    else:
                        lives_remaining_var.set(lives_remaining_var.get()-1)
                        b['relief'] = 'raised'
                        im_path = directory + '\\Images\\Mines\\'
                        im_size = self.button_size - 6
                        #If there are no lives left (game is lost).
                        if lives_remaining_var.get() == 0:
                            self.time_passed = tm.time() - self.start
                            self.start = 0
                            self.game_state = 'lost'
                            timer_var.set("%03d" % (min(self.time_passed + 1, 999)))
                            timer_label['fg'] = 'red'
                            face_button['image'] = self.face_images['lost1face']
                            n = -self.final_grid[coord]/9
                            im_name = 'red%smine%02d' % (n, im_size)
                            b['image'] = b.image = PhotoImage(name=im_name, file=im_path + im_name + '.ppm')
                            b['bg'] = '#%02x%02x%02x' % bg_colours['red']
                            mine_image = PhotoImage(name='1mine%02d'%im_size, file=im_path + '1mine%s'%im_size + '.ppm')
                            for c in self.buttons:
                                b1 = self.buttons[c]
                                if (self.grid[c] < -1 and self.grid[c] != self.final_grid[c]):
                                    buttontexts[b1].set("X")
                                    b1['image'] = b1.image = ''
                                elif self.grid[c] == -1 and self.final_grid[c] < -7:
                                    n = -self.final_grid[c]/9
                                    if b1.coord != b.coord:
                                        if n == 1:
                                            b1['image'] = b1.image = mine_image
                                        else:
                                            im_name = '%smine%s' % (n, im_size)
                                            b1['image'] = b1.image = PhotoImage(name=im_name, file=im_path + im_name + '.ppm')
                            return
                        else:
                            self.grid[coord] = self.final_grid[coord]
                            n = -self.final_grid[coord]/9
                            im_name = 'blue%smine%02d' % (n, im_size)
                            b['image'] = b.image = PhotoImage(name=im_name, file=im_path + im_name + '.ppm')
                            b['bg'] = '#%02x%02x%02x' % bg_colours['blue']
                            n = min(3, lives_remaining_var.get())
                            face_button['image'] = self.face_images['ready%sface'%n]
                            mines_var.set("%03d" % (self.mines_grid.sum() + np.where(self.grid<-1, self.grid, 0).sum()/9))
                            if self.mines_grid.sum() + np.where(self.grid<-1, self.grid, 0).sum()/9 < 0:
                                mines_label.config(bg='red', fg='black')
                            else:
                                mines_label.config(bg='black', fg='red')
                    if (np.where(self.grid < 0, -9, self.grid) == np.where(self.final_grid < -7, -9, self.final_grid)).all():
                        self.time_passed = tm.time() - self.start
                        self.start = 0
                        self.game_state = 'won'
                        mines_var.set("000")
                        timer_var.set("%03d" % (min(self.time_passed + 1, 999)))
                        timer_label['fg'] = 'red'
                        n = min(3, lives_remaining_var.get())
                        face_button['image'] = self.face_images['won%sface'%n]
                        for c in self.buttons:
                            b1 = self.buttons[c]
                            if self.grid[c] == -1 and self.final_grid[c] < 0:
                                n = -self.final_grid[c]/9
                                buttontexts[b1].set(mineflags[n-1])
                                b1['image'] = b1.image = self.flag_images[n]
                        if self.drag_click == 'off':
                            set_highscore()
                            #Otherwise wait for left release.
                        return

        def rightdown(event):
            coord = tuple(map(int, event.widget.bindtags()[0].split()))
            self.original_coord = self.coord_rightclicked = coord
            if self.game_state == 'active':
                self.rightbuttondown = True
            self.blockclick = False
            # combinedclick() will be implemented on release.
            if self.leftbuttondown:
                self.blockclick = True
                if self.grid[coord] >= 0:
                    for c in self.get_neighbours(coord, self.detection):
                        if self.grid[c] == -1:
                            self.buttons[c]['relief'] = 'sunken'
                return
            b = self.buttons[coord]
            if create_var.get() and per_cell_var.get() > 0:
                    self.per_cell = per_cell_var.get()
            elif self.game_state in ['won', 'lost'] or (b.image and 'mine' in b.image.name):
                    return
            self.coord_flagged = coord
            if self.grid[coord] == -1:
                self.grid[coord] = -9
                b['image'] = b.image = self.flag_images[1]
            elif self.grid[coord] < -1:
                if self.grid[coord] > -9*self.per_cell:
                    self.grid[coord] -= 9
                    n = -self.grid[coord]/9
                    buttontexts[b].set(mineflags[n-1])
                    b['image'] = b.image = self.flag_images[n]
                else:
                    buttontexts[b].set("")
                    self.grid[coord] = -1
                    b['image'] = b.image = ''
            else:
                self.coord_flagged = None
            mines_var.set("%03d" % (abs(self.mines_grid.sum() + np.where(self.grid<-7, self.grid, 0).sum()/9)))
            if not create_var.get() and self.mines_grid.sum() - np.where(self.grid<-7, -self.grid/9, 0).sum() < 0:
                mines_label.config(bg='red', fg='black')
            else:
                mines_label.config(bg='black', fg='red')

        def doubleleftclick(event):
            coord = tuple(map(int, event.widget.bindtags()[0].split()))
            b = self.buttons[coord]
            if buttontexts[b].get() in mineflags and self.per_cell > 2 and (self.start or create_var.get()):
                self.blockclick = True
                self.reset_button(b, buttontexts[b])
                self.grid[coord] = -1
                mines_var.set("%03d" % (abs(self.mines_grid.sum() + np.where(self.grid<-1, self.grid, 0).sum()/9)))
                if not create_var.get() and self.mines_grid.sum() + np.where(self.grid<-1, self.grid, 0).sum()/9 < 0:
                    mines_label.config(bg='red', fg='black')
                else:
                    mines_label.config(bg='black', fg='red')

        def leftdown(event):
            coord = event.widget.coord
            #Used in leftclick() when dragging with combinedclick to sink original button.
            self.original_coord = coord
            self.leftbuttondown = True
            self.blockclick = False
            self.coord_leftclicked = coord
            if self.game_state in ['active', 'ready']:
                n = min(3, lives_remaining_var.get())
                face_button['image'] = self.face_images['active%sface'%n]
            c = self.coord_rightclicked
            if self.rightbuttondown and self.grid[c] >= 0 and (not self.coord_flagged or self.grid[self.coord_flagged] < -1):
                for c1 in self.get_neighbours(c, self.detection):
                    if self.grid[c1] == -1:
                        self.buttons[c1]['relief'] = 'sunken'
            elif self.drag_click == 'single' and self.game_state == 'active':
                if self.grid[coord] == -1:
                    self.leftbuttondown = False
                leftclick(actual_click=False)

        def rightrelease(event):
            coord = self.coord_rightclicked
            self.rightbuttondown = False
            self.coord_flagged = None
            if self.leftbuttondown:
                self.blockclick = True
                combinedclick(coord)
            elif create_var.get() and self.grid[coord] >= 0 and not self.blockclick:
                self.reset_button(self.buttons[coord], buttontexts[self.buttons[coord]])
                self.grid[coord] = -1
            # if self.game_state == 'active' and self.leftbuttondown and self.coord_leftclicked != coord:
            #     self.buttons[self.original_coord]['relief'] = 'sunken'

        def leftrelease(event):
            #This is the coord originally clicked.
            coord = event.widget.coord
            n = min(3, lives_remaining_var.get())
            if n > 0 and self.game_state in ['ready', 'active']:
                face_button['image'] = self.face_images['ready%sface'%n]
            #Only click a button if the mouse was clicked on one of the button widgets in mainframe. Avoids this being run when menus are used.
            #Used to click buttons that aren't originally clicked, or to run combinedclick() if right button is down.
            if self.leftbuttondown and (self.rightbuttondown or (self.coord_leftclicked != coord and (self.game_state == 'ready' or (self.drag_click == 'off' and self.game_state == 'active')))):
                leftclick()
            if self.game_state == 'won' and self.drag_click == 'single' and not self.score_checked:
                set_highscore()
            self.leftbuttondown = False

        def motion(leftorright):
            def action(event):
                coord = tuple(map(int, event.widget.bindtags()[0].split()))
                prev_coord = self.coord_leftclicked if leftorright == 'left' else self.coord_rightclicked
                c = (coord[0]+event.y/self.button_size, coord[1]+event.x/self.button_size)
                if c in [(u, v) for u in range(self.shape[0]) for v in range(self.shape[1])] and c != prev_coord:
                    if self.rightbuttondown and self.leftbuttondown:
                        old_neighbours = self.get_neighbours(self.coord_rightclicked, self.detection, 1)
                        new_neighbours = self.get_neighbours(c, self.detection, 1)
                        for c1 in {i for i in new_neighbours if self.grid[i] == -1}:
                            self.buttons[c1]['relief'] = 'sunken'
                        for c1 in {i for i in old_neighbours if self.grid[i] == -1} - new_neighbours:
                            self.buttons[c1]['relief'] = 'raised'
                    elif leftorright == 'left' and not self.blockclick:
                        if self.grid[prev_coord] == -1 and (self.game_state == 'ready' or self.drag_click == 'off'):
                            self.buttons[prev_coord]['relief'] = 'raised'
                        #For when the mouse is moved from the first button clicked.
                        elif self.drag_click == 'single' and prev_coord == coord and self.game_state in ['lost', 'won', 'active']:
                            leftclick(coord)
                        if self.grid[c] == -1 and self.game_state in ['ready', 'active']:
                            if self.drag_click == 'single' and self.game_state == 'active':
                                leftclick(c, actual_click=False)
                            elif self.drag_click == 'off' or (self.drag_click == 'single' and self.game_state == 'ready'):
                                self.buttons[c]['relief'] = 'sunken'
                    if self.rightbuttondown:
                        self.coord_rightclicked = c
                    if self.leftbuttondown:
                        self.coord_leftclicked = c
            return action

        def combinedclick(coord):
            #Either the left or right button has been released.
            neighbours = self.get_neighbours(coord, self.detection, 1)
            for c in neighbours:
                if self.grid[c] < 0:
                    self.buttons[c]['relief'] = 'raised'
            if self.grid[coord] >= 0:
                neighbouring_mines = 0
                for c in neighbours:
                    if self.grid[c] < -1:
                        neighbouring_mines -= self.grid[c]/9
                    if neighbouring_mines > self.grid[coord]:
                        return
                if neighbouring_mines == self.grid[coord]:
                    for c in neighbours:
                        if self.grid[c] == -1:
                            leftclick(c, actual_click=False)

        def make_button(coord, bindings=True):
            f = Frame(mainframe, width=self.button_size, height=self.button_size)
            frames[coord] = f
            f.rowconfigure(0, weight=1) #enables button to fill frame...
            f.columnconfigure(0, weight=1)
            f.grid_propagate(False) #disables resizing of frame
            f.grid(row=coord[0], column=coord[1])
            btext = StringVar()
            b = Button(f, bd=3, takefocus=0, textvariable=btext, font=self.cellfont, command=leftclick)
            buttontexts[b] = btext #Should the button really be the key??
            self.buttons[coord] = b
            b.grid(sticky='nsew')
            b.bindtags(tuple([coord]+list(b.bindtags())))
            b.coord = coord
            b.bind('<Button-3>', rightdown)
            b.bind('<Double-Button-1>', doubleleftclick)
            b.bind('<Button-1>', leftdown)
            b.bind('<ButtonRelease-3>', rightrelease)
            b.bind('<ButtonRelease-1>', leftrelease)
            b.bind('<B1-Motion>', motion('left'))
            b.bind('<B3-Motion>', motion('right'))
            b.image = ''

        mainframe = Frame(root, bd=10, relief='ridge')
        mainframe.pack()
        frames = dict()
        self.buttons = dict()
        buttontexts = dict()
        for coord in [(u, v) for u in range(self.shape[0]) for v in range(self.shape[1])]:
            make_button(coord)

        self.start = 0
        TimerThread(threading.active_count(), self, timer_var).start()
        mainloop()
        self.keeptimer = False

        if per_cell_var.get() > 0:
            self.per_cell = per_cell_var.get()
        self.first_success = first_success_var.get()
        self.detection = detection_options[detection_var.get()]
        settings = dict()
        for s in default_settings:
            settings[s] = getattr(self, s)
        with open(directory + r'\Settings.txt', 'w') as f:
            f.write(str(settings))

        tm.sleep(1)
        return


def display_grid(array, mines=False):
    if mines:
        array *= -9
    replacements = dict([(-18,':'), (-27,'%'), (-36,'#'), (-45,'&'), (-54,'$'), (-9,'*'), (0,''), (-1,''), (-8,'X')])
    root = Tk()
    for coord in [(u, v) for u in range(array.shape[0]) for v in range(array.shape[1])]:
        f = Frame(root, width=16, height=16)
        f.rowconfigure(0, weight=1) #enables button to fill frame...
        f.columnconfigure(0, weight=1)
        f.grid_propagate(False) #disables resizing of frame
        f.grid(row=coord[0], column=coord[1])
        text = replacements[array[coord]] if array[coord] in replacements else str(array[coord])
        colour = number_colours[array[coord]] if array[coord] in number_colours else 'black'
        b = Button(f, bd=2.4, takefocus=0, text=text, font=cellfont, fg=colour)
        b.grid(sticky='NSEW')
        if array[coord] >= 0:
            b['relief'] = 'sunken'
            b['bd'] = 0.5
    mainloop()
    return



def prettify_grid(array, do_print=False):
        replacements = [('-18','@'), ('-27','%'), ('-36','&'), ('-45','$'), ('-9','#'), ('\n  ',' '),
                        ('0','.'), ('-1','='), ('-8','X'), ('   ',' '), ('  ',' '), ('[ ','[')]
        ret = str(array)
        for r in replacements:
            ret = ret.replace(*r)
        if do_print:
            print ret
        else:
            return ret

class PlayThread(threading.Thread):
    def __init__(self, threadID, minefield, runargs):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.runargs = runargs
        self.minefield = minefield
    def run(self):
        print "Thread {} for playing the game is running.".format(self.threadID)
        self.minefield.play(*self.runargs)
        print "Thread {} ended.".format(self.threadID)

class DispThread(threading.Thread):
    #Not used.
    def __init__(self, threadID, minefield, runargs):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.runargs = runargs
        self.minefield = minefield
    def run(self):
        print "Thread {} for displaying grids is running.".format(self.threadID)
        self.minefield.display_grid(*self.runargs)
        print "Thread {} ended.".format(self.threadID)

class TimerThread(threading.Thread):
    def __init__(self, threadID, game, timervar):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.game = game
        self.timervar = timervar
    def run(self):
        print "Thread %d for the timer is running." % self.threadID
        self.game.keeptimer = True
        while self.game.keeptimer:
            if self.game.start:
                time_passed = tm.time() - self.game.start
                self.timervar.set("%03d" % (min(time_passed+1, 999)))
                tm.sleep(1 - time_passed % 1 + 0.05)
            else:
                tm.sleep(1)
        print "Thread %d ended." % self.threadID



#My record of 68.7 seconds (142 3bv). Mine coordinates are below.
example = [(0, 0), (0, 11), (0, 12), (0, 14), (1, 3), (2, 3), (2, 4), (2, 8), (3, 2), (3, 3), (3, 5), (3, 15), (4, 5), (4, 7), (4, 9), (4, 11), (5, 2), (5, 6), (6, 10), (7, 8), (8, 3), (8, 10), (9, 2), (9, 12), (10, 4), (10, 7), (10, 13), (11, 2), (11, 4), (11, 7), (11, 8), (11, 9), (11, 13), (12, 9), (13, 3), (13, 7), (13, 10), (13, 15), (14, 3), (15, 7), (15, 10), (16, 0), (16, 2), (16, 9), (16, 11), (16, 13), (17, 0), (17, 7), (17, 9), (18, 1), (18, 5), (18, 9), (18, 10), (18, 13), (19, 10), (19, 15), (20, 3), (20, 6), (20, 7), (20, 15), (21, 3), (21, 5), (22, 2), (22, 6), (22, 8), (22, 12), (22, 13), (22, 14), (22, 15), (23, 0), (23, 1), (23, 8), (23, 9), (23, 12), (23, 14), (24, 3), (24, 4), (24, 10), (24, 11), (25, 0), (25, 1), (25, 3), (25, 7), (26, 8), (26, 9), (26, 11), (26, 12), (27, 9), (27, 14), (27, 15), (28, 8), (28, 9), (28, 10), (28, 11), (28, 14), (29, 6), (29, 7), (29, 10), (29, 14)]



if __name__ == '__main__':
    g = Game()
    #g.thread_play()
    #display_grid(Minefield(per_cell=3).mines_grid, 1)


