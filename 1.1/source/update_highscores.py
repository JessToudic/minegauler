"""Used to update the highscores to new format and include them."""

import time as tm
import os
from os.path import join
import json
from shutil import copy2 as copy_file

from resources import *

__version__ = version

def update_data(path, version):
    """Returns data in the new format, ready to be added to current file."""
    version = LooseVersion(version)
    new_data = []
    if version < '1.0':
        with open(path, 'r') as f:
            old_data = eval(f.read())
        stop = raw_input(
            'Old highscores have no encryption key, include anyway? ' +
            '(Hit Enter for yes, otherwise type something.) ')
        if stop:
            return []
        for settings, old_entry_list in old_data.items():
            for old_entry in old_entry_list:
                if not old_entry.has_key('Zoom'):
                    zoom = 16
                elif old_entry['Zoom'] == 'variable':
                    zoom = None
                else:
                    zoom = round(old_entry['Zoom']*16/100, 0)
                if settings[2] == 1.7:
                    detection = 1.8
                else:
                    detection = settings[2]
                new_entry = {
            'name':         old_entry['Name'],
            'level':        settings[0],
            'lives':        settings[4],
            'per cell':     settings[1],
            'detection':    detection,
            'drag':         True if settings[3] == 'single' else False,
            'distance to':  False,
            'time':         old_entry['Time'],
            '3bv':          old_entry['3bv'],
            '3bv/s':        old_entry['3bv/s'],
            'proportion':   1,
            'flagging':     1 if old_entry['Flagging'] == 'F' else 0,
            'date':         tm.mktime(tm.strptime(
                old_entry['Date'], '%d %b %Y %X')),
            'lives rem':    old_entry['Lives remaining'],
            'first success':old_entry['First success'],
            'zoom':         zoom, # See above
            'coords':       old_entry['Mine coords']}
                new_entry['key'] = encode_highscore(new_entry)
                new_data.append(new_entry)
    elif version == '1.0':
        with open(path, 'r') as f:
            old_data = [h for h in json.load(f) if h['proportion'] == 1 and
                h.has_key('key') and h['lives'] == 1]
        new_data = old_data[:]
        for d in new_data:
            for old, new in [('level', 'diff'), ('per cell', 'per_cell'),
                ('drag', 'drag_select'), ('zoom', 'button_size'),
                ('distance to', 'distance_to'),
                ('lives rem', 'lives_remaining'),
                ('first success', 'first_success')]:
                try:
                    d[new] = d.pop(old)
                except KeyError:
                    d[new] = None # No first success?
    elif version < '1.1.1':
        with open(path, 'r') as f:
            new_data = [h for h in json.load(f) if h['proportion'] == 1 and
                h.has_key('key') and h['lives'] == 1]
    elif version < '1.1.2':
        old_encode = lambda h: (
            (sum([c[0]*c[1] for c in h['coords']])
                if h.has_key('coords') else 0) +
            int(10*h['date']/float(h['time'])) +
            int(100*float(h['3bv/s'])) + h['3bv'] -
            reduce(lambda x, y: x + ord(y), h['name'], 0) + 3*h['lives'] +
            int(50*h['detection']) + 7*h['per_cell'] +
            19*int(h['drag_select']) +
            12*int(h['distance_to']) + int(11*(h['proportion'] - 1)))
        with open(path, 'r') as f:
            new_data = [h for h in json.load(f) if h['key'] == old_encode(h)]
    else:
        with open(path, 'r') as f:
            new_data = json.load(f)
    return new_data

def include_data(data, direc, check=True, save=True):
    """
    Include the converted old data in the current data file, which is
    first backed up."""
    copy_file(join(direc, 'data.txt'), join(direc, 'databackup{}.txt'.format(
        tm.asctime()).replace(':', '.')))
    with open(join(direc, 'data.txt'), 'r') as f:
        cur_data = json.load(f)
    all_data = cur_data[:]
    if check:
        data = [h for h in data if h.has_key('key') and
            h['key'] == encode_highscore(h)]
    for d in data:
        if not check:
            d['key'] = encode_highscore(d)
        matches = [h for h in all_data if h['date'] == d['date'] and
            h['key'] == d['key']]
        if not matches:
            all_data.append(d)
        if len(matches) > 1:
            print "Possible duplicate found in highscores:\n", matches[0]
    print "Added {} data entries.".format(len(all_data) - len(cur_data))
    if save:
        with open(join(direc, 'data.txt'), 'w') as f:
            json.dump(sorted(all_data, key=lambda x: x['date']), f)
    else:
        return all_data


if __name__ == '__main__':
    from main import data_direc
    while True:
        path = raw_input("Input old data file path:\n")
        if not path:
            break
        version = raw_input("Input the version number: ")
        if not version:
            version = __version__
        check = raw_input("Bypass key checking? (Enter for yes) ")
        data = update_data(path, version)
        include_data(data, data_direc, check)