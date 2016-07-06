from pprint import pprint
import os
import shutil
from base import find_class_paths_and_iterate
import difflib
import re
from base import verbose

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

    def rename_package(self, old_package, new_package):
        if not len(old_package) == len(new_package):
            print('PACKAGE LENGTH NOT CORRECT')
            return
        old_path = os.sep.join(old_package)
        new_path = os.sep.join(new_package)
        to_change = [list(x) for x in self.to_read if x[2] == old_path]
        for e in to_change:
            e.append(e[0].replace(os.path.join('', old_path), ''))

        to_avoid = re.compile(r'(\s*const-string[/jumbo]?\s.*,\s".*")')

        # Create new folders and copy files there:
        self.create_and_copy(to_change, new_path)
        self.to_read = find_class_paths_and_iterate(self.base_path)

        for class_file in self.to_read:
            change = False
            with open(os.path.join(class_file[0], class_file[1]), 'r') as f:
                content = f.read()
                new_content = ''
                for line in iter(content.splitlines()):
                    search = to_avoid.findall(line)
                    if len(search) == 0:
                        new_content += line.replace('L' + '/'.join(old_package), 'L' + '/'.join(new_package))
                    else:
                        new_content += line
                    new_content += os.linesep
                if not new_content == content:
                    change = True
                    if verbose:
                        print('CHANGE IN {}'.format(class_file))
                        for s in difflib.context_diff(content, new_content):
                            print(s)
            if change:
                os.remove(os.path.join(class_file[0], class_file[1]))
                with open(os.path.join(class_file[0], class_file[1]), 'a+') as f:
                    f.write(new_content)

    def rename_function(self, package, java_class, function, new_name):
        raise NotImplementedError()

        pattern = re.compile(r'\.method\s(public|private|protected)*\s*(static)*\s*([\w\s<>;]*)\((.*)\)(.*)')
        path = os.sep.join(package)
        location = [x for x in self.to_read if x[1] == java_class + '.smali' and x[2] == path]
        if len(location) > 1 or len(location) == 0:
            print('Function not unique or not found. What do?')
            return
        location = location[0]
        print(location)
        replaces = []
        with open(os.path.join(location[0], location[1]), 'r') as f:
            content = f.read()
            search = pattern.findall(content)
            for result in search:
                if result[2] == function:
                    static_append = ''
                    if not result[1] == '':
                        static_append = ' ' + result[1]
                    replaces.append(
                        (
                            '.method {}{} {}({}){}'.format(result[0], static_append, result[2], result[3], result[4]),
                            '.method {}{} {}({}){}'.format(result[0], static_append, new_name, result[3], result[4])
                         )
                    )
        for replace in replaces:
            content = content.replace(replace[0], replace[1])
        os.remove(os.path.join(location[0], location[1]))
        with open(os.path.join(location[0], location[1]), 'a+') as f:
            f.write(content)
