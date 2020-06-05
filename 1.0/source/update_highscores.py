"""Used to update the highscores to new format and include them."""

import time as tm
import os
import json
from shutil import copy2 as copy_file

from main01 import (__version__ as main_version, data_direc, encode_highscore)


def update_data(direc, version='1.0'):
    """Returns data in the new format, ready to be added to current file."""
    new_data = []
    if version[0] == '0':
        with open(direc, 'r') as f:
            old_data = eval(f.read())
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
        with open(direc, 'r') as f:
            new_data = json.load(f)
    return new_data

def include_data(data):
    """
    Include the converted old data in the current data file, which should
    first be backed up."""
    copy_file(os.path.join(data_direc, 'data.txt'),
        os.path.join(data_direc, 'databackup{}.txt'.format(
            tm.asctime()).replace(':', '')))
    with open(os.path.join(data_direc, 'data.txt'), 'r') as f:
        cur_data = json.load(f)
    all_data = cur_data[:]
    for d in data:
        if not (d['date'] in [h['date'] for h in all_data] and
            encode_highscore(d) in [encode_highscore(h) for h in all_data if
                h['date'] == d['date']]):
            all_data.append(d)
    print "Added {} data entries.".format(len(all_data) - len(cur_data))
    all_data.sort(key=lambda x: x['date'])
    with open(os.path.join(data_direc, 'data.txt'), 'w') as f:
        json.dump(all_data, f)


if __name__ == '__main__':
    while True:
        directory = raw_input("Input old data file path:\n")
        if not directory:
            break
        version = raw_input("Input the version number: ")
        if not version:
            version = main_version
        data = update_data(directory, version)
        include_data(data)