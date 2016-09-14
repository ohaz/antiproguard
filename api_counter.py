from threading import Lock
import os
import re
from concurrent.futures import ThreadPoolExecutor
import json
from pprint import pprint
import copy
from colorama import Fore, Style
import base

__author__ = 'ohaz'

# ATTENTION: This is an old, unused file!

class APICounter:

    def __init__(self, threads, to_read):
        self.lock = Lock()
        self.pattern = re.compile(r'(invoke-\w+)\s\{([\w,\s]+)\},\sL((java)[/\w$0-9]+);->(.*)')
        self.amount_dict = {}
        self.threads = threads
        self.to_read = to_read
        self.compared = []
        self.shortened = []
        # self.database = base.database['api_counter']

    def generate_sub_dict(self, path, key):
        current = self.amount_dict
        for k in path:
            current = current[k]
        return current.setdefault(key, {})

    def get_sub_dict(self, path):
        current = self.amount_dict
        for k in path:
            current = current[k]
        return current

    def read_and_accumulate(self, path, f, start):
        keys = start.split('\\')
        self.lock.acquire()
        for pos, key in enumerate(keys):
            self.generate_sub_dict(keys[:pos], key)
        self.lock.release()
        own = {}
        with open(os.path.join(path, f), 'r') as file:
            content = file.read()
            for pt in self.pattern.findall(content):
                key = '{} ({}) {}->{}'.format(pt[0], pt[1], pt[2], pt[4])
                own[key] = own.get(key, 0) + 1
        amount = 0
        for k in own:
            amount += own[k]
        own['.calls'] = copy.deepcopy(own)
        own['.overall'] = amount
        self.lock.acquire()
        self.get_sub_dict(keys)[f] = own
        self.lock.release()

    def fold_dict(self, dct):
        if '.overall' not in dct:
            dct['.overall'] = 0
            dct['.calls'] = {}

        for key in dct:
            if key in ['.overall', '.calls']:
                continue
            child = dct[key]
            if not key.endswith('.smali'):
                self.fold_dict(child)
            dct['.overall'] += child['.overall']
            for entry in child['.calls']:
                dct['.calls'][entry] = dct['.calls'].get(entry, 0) + child['.calls'][entry]

        return dct

    def remove_create_dump(self, path, ending, jsdct):
        whole_path = os.path.basename(path) + ending
        if os.path.exists(whole_path):
            os.remove(whole_path)
        with open(whole_path, 'a+') as f:
            json.dump(jsdct, f)

    def shorten_folded(self, dct):
        if not isinstance(dct, dict):
            return
        if '.calls' in dct:
            del dct['.calls']
        for key in dct:
            if key in ['.overall', '.calls']:
                continue
            self.shorten_folded(dct[key])
        return dct

    def compare(self, dct, path='', guess=None):
        if not isinstance(dct, dict):
            return

        for lib_key in self.database:
            lib = self.database[lib_key]
            for version in lib['versions']:
                if version['data']['.overall'] in range(max(0, int(dct['.overall'] * 0.975)), int(dct['.overall'] * 1.25)):
                    guess = lib
                    error = abs(100 - (dct['.overall'] * 1.0) / ((version['data']['.overall'] * 1.0) / 100))
                    # print(Fore.YELLOW+'Guessing that', path, 'equals', lib['fullname'], 'V:', version['version'], 'with error:',
                    #       Fore.RED+'{:.5f}%'.format(error), Style.RESET_ALL)
                    self.compared.append((path[:-1], lib, error))
        for key in dct:
            if key in ['.overall', '.calls']:
                continue
            self.compare(dct[key], path+key+'.', guess)

    def count(self, path):
        with ThreadPoolExecutor(max_workers=self.threads) as executor:
            for work in self.to_read:
                executor.submit(self.read_and_accumulate, work[0], work[1], work[2])
        if base.verbose: self.remove_create_dump(path, '_unfolded.json', self.amount_dict)
        folded = self.fold_dict(copy.deepcopy(self.amount_dict))
        if base.verbose: self.remove_create_dump(path, '_folded.json', folded)
        self.shortened = self.shorten_folded(copy.deepcopy(folded))
        if base.verbose: self.remove_create_dump(path, '_shortened.json', self.shortened)
        if base.verbose: print('>> Generated', os.path.basename(path) + '.json, _unfolded.json, _folded.json, _shortened.json',
              'containing the api call counts')
        return folded

    def count_and_compare(self, path):
        folded = self.count(path)
        print('>> Comparing with database...')
        self.compare(self.shortened)
        return folded
