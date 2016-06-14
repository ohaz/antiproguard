from pprint import pprint
import os
import shutil
from base import find_class_paths_and_iterate
import difflib

__author__ = 'ohaz'

class Renamer:

    def __init__(self, to_read, base_path):
        self.to_read = to_read
        self.base_path = base_path

    def create_and_copy(self, to_change, new_path):
        for e in to_change:
            try:
                os.makedirs(os.path.join(e[3], new_path))
            except OSError as err:
                # Already created correct folder
                pass
            shutil.copyfile(os.path.join(e[0], e[1]), os.path.join(e[3], new_path, e[1]))
            # Deleting old class
            os.remove(os.path.join(e[0], e[1]))

    def rename(self, old_package, new_package):
        if not len(old_package) == len(new_package):
            print('PACKAGE LENGTH NOT CORRECT')
            return
        old_path = os.sep.join(old_package)
        new_path = os.sep.join(new_package)
        to_change = [list(x) for x in self.to_read if x[2] == old_path]
        for e in to_change:
            e.append(e[0].replace(os.path.join('', old_path), ''))

        # Create new folders and copy files there:
        self.create_and_copy(to_change, new_path)
        self.to_read = find_class_paths_and_iterate(self.base_path)

        for class_file in self.to_read:
            change = False
            with open(os.path.join(class_file[0], class_file[1]), 'r') as f:
                content = f.read()
                new_content = content.replace('L'+'/'.join(old_package), 'L'+'/'.join(new_package))
                if not new_content == content:
                    change = True
            if change:
                os.remove(os.path.join(class_file[0], class_file[1]))
                with open(os.path.join(class_file[0], class_file[1]), 'a+') as f:
                    f.write(new_content)

