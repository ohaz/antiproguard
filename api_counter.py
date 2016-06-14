from threading import Lock
import os
import re
from concurrent.futures import ThreadPoolExecutor
import json

__author__ = 'ohaz'


class APICounter:

    def __init__(self, threads, to_read):
        self.lock = Lock()
        self.pattern = re.compile(r'(invoke-\w+)\s\{([\w,\s]+)\},\sL((android|java)[/\w$0-9]+);->(.*)')
        self.amount_dict = {}
        self.threads = threads
        self.to_read = to_read

    def read_and_accumulate(self, path, f, start):
        with open(os.path.join(path, f), 'r') as file:
            content = file.read()
            self.lock.acquire()
            self.amount_dict[os.path.join(start, f)] = len(self.pattern.findall(content))
            self.lock.release()

    def fold_dict(self):
        new_dict = {}
        for k in self.amount_dict:
            v = self.amount_dict[k]
            spl = k.split(os.sep)
            new_key = spl[0]
            if len(spl) > 2:
                new_key = os.path.join(new_key, spl[1])
            if len(spl) > 3:
                new_key = os.path.join(new_key, spl[2])
            new_dict[new_key] = new_dict.get(new_key, 0) + v
        return new_dict

    def count(self, path):
        with ThreadPoolExecutor(max_workers=self.threads) as executor:
            for work in self.to_read:
                executor.submit(self.read_and_accumulate, work[0], work[1], work[2])

        folded = self.fold_dict()
        if os.path.exists(os.path.basename(path) + '.json'):
            os.remove(os.path.basename(path) + '.json')
        with open(os.path.basename(path) + '.json', 'a+') as f:
            json.dump(folded, f)
        print('>> Generated', os.path.basename(path) + '.json', 'containing the api call counts')
        return folded
