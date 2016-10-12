from pprint import pprint
import os
import difflib
import re

from tqdm import tqdm

from base import verbose
from distutils import dir_util
import shutil
import apkdb

__author__ = 'ohaz'


class Renamer:
    """
    Class that tries to rename Packages, Classes and Methods
    """

    def __init__(self, root, eops):
        """
        Initializes a new Renamer
        
        :param root: The root node of a package/file tree
        :param eops: A list of eops
        """
        self.root = root
        self.eops = eops
        # Avoid const-string replacements
        # This is so that things like String("La/b/c/d/"); don't get renamed
        self.to_avoid = re.compile(r'(\s*const-string[/jumbo]?\s.*,\s".*")')
        self.method_call_name = re.compile(r'\s*.method(?:.*)\s(.*\(.*\).*)')
        self.method_name = re.compile(r'\s*.method(?:.*)\s(.*)\(.*\).*')

    def rename_packages(self):
        """
        Rename packages using their hints
        
        :return: void
        """
        print('Renaming calls')
        for eop in tqdm(self.eops):
            if len(eop.hints) == 0:
                continue
            # Take the first hint, it's usually the correct one
            lib = eop.hints[0]
            other_package = '.'.join([lib[0].base_package, lib[1].name]) if len(lib[1].name) > 0 else lib[
                0].base_package
            # Rename all calls to this package
            self.rename_calls(eop.get_full_package(), other_package)
        print('Changing package structure')
        for eop in tqdm(self.eops):
            if len(eop.hints) == 0:
                continue
            special = eop.search_special()
            lib = eop.hints[0]
            other_package = '.'.join([lib[0].base_package, lib[1].name]) if len(lib[1].name) > 0 else lib[
                0].base_package
            other_path = other_package.replace('.', os.sep)
            # Move the package to it's new location
            self.create_and_copy(eop.get_full_path(), os.path.join(special.get_full_path(), other_path))

    def rename_classes(self):
        """
        Rename Classes using their hints
        
        :return: void
        """
        for eop in tqdm(self.eops):
            file_ids_done = list()
            if len(eop.hints) == 0:
                continue
            lib = eop.hints[0]
            active_package = '.'.join([lib[0].base_package, lib[1].name]) if len(lib[1].name) > 0 else lib[
                0].base_package
            for file in eop.get_files():
                if not file.is_obfuscated_itself():
                    # Skip files that don't seem to be obfuscated
                    continue
                for hint in file.hints:
                    if hint in file_ids_done:
                        continue
                    apkfile = apkdb.session.query(apkdb.File).filter(apkdb.File.id == hint).first()
                    apkfile_package_name = '.'.join(
                        [apkfile.package.library.base_package, apkfile.package.name]) if len(
                        apkfile.package.name) > 0 else apkfile.package.library.base_package
                    if apkfile_package_name != active_package:
                        continue
                    old_package = file.get_full_package()
                    # Rename this file and rename all calls to this file
                    if self.rename_this_file(file, apkfile, apkfile_package_name):
                        file_ids_done.append(hint)
                        self.rename_calls(old_package, apkfile_package_name + '.' + apkfile.name)

    def rename_this_file(self, file, new, apkfile_package_name):
        """
        Rename this file to a new name
        
        :param file: the file to rename
        :param new: the new file (from db)
        :param apkfile_package_name: the package of the apkfile
        :return: True if works, else False
        """
        new_package = apkfile_package_name + '.' + new.name
        new_package_in_path = '/'.join(new_package.split('.'))
        new_replace = 'L' + new_package_in_path + ';'
        old_package = file.get_full_package()
        old_package_in_path = '/'.join(old_package.split('.'))
        old_replace = 'L' + old_package_in_path + ';'
        new_filename = os.path.join(os.path.dirname(file.get_full_path()), new.name + '.smali')
        if os.path.exists(new_filename):
            # If target file already exists, this probably was not the correct deobfuscation. Skip it
            return False
        with open(file.get_full_path(), 'r') as readfile:
            with open(new_filename, 'w+') as writefile:
                content = readfile.read()
                # read line by line and write line by line, replacing all occurrences of the old name with the new one
                for line in content.splitlines():
                    search = self.to_avoid.findall(line)
                    if len(search) == 0:
                        writefile.write(line.replace(old_replace, new_replace))
                    else:
                        writefile.write(line)
                    writefile.write(os.linesep)
        if os.path.exists(new_filename):
            os.remove(file.get_full_path())
            file.name = new.name + '.smali'
            return True
        return False

    def rename_calls(self, old_package, new_package):
        """
        Rename calls targeted on the old package to the new package
        
        :param old_package: the old package, prior to renaming
        :param new_package: the new package, post renaming
        :return: void
        """
        files = []
        for f_eop in self.eops:
            files.extend(f_eop.get_files())
        for class_file in files:
            # Looping over all files
            change = False
            with open(class_file.get_full_path(), 'r') as f:
                content = f.read()
                new_content = ''
                for line in content.splitlines():
                    search = self.to_avoid.findall(line)
                    if len(search) == 0:
                        # Replace the old package name with the new one.
                        # Packages have the format La/b/c/d/e;
                        # with e being the class and a,b,c,d being packages and subpackages
                        new_content += line.replace('L' + '/'.join(old_package.split('.')) + '/',
                                                    'L' + '/'.join(new_package.split('.')) + '/')
                    else:
                        new_content += line
                    if len(line) > 0:
                        new_content += os.linesep
                if not new_content == content:
                    change = True
                    if verbose:
                        print('CHANGE IN {}'.format(class_file))
                        for s in difflib.context_diff(content, new_content):
                            print(s)
            if change:
                # Replace the old file with the fixed new one
                os.remove(class_file.get_full_path())
                with open(class_file.get_full_path(), 'w+') as f:
                    f.write(new_content)

    def create_and_copy(self, old_path, new_path):
        """
        Create a package with a deobfuscated name and copy all contents of the old one to the new one
        
        :param old_path: the path prior to the copy process
        :param new_path: the path post to the copy process
        :return: void
        """
        if old_path == new_path:
            return
        try:
            os.makedirs(new_path)
        except OSError as err:
            pass
        dir_util._path_created = {}
        dir_util.copy_tree(old_path, new_path)
        shutil.rmtree(old_path)

    def rename_methods(self):
        """
        Rename method definitions and calls to new name
        
        :return: void
        """
        for eop in self.eops:
            if len(eop.hints) == 0:
                continue
            lib = eop.hints[0]
            for file in tqdm(eop.get_files()):
                if not file.is_obfuscated_itself() or len(file.hints) == 0:
                    # Skip files that don't seem to be obfuscated
                    continue
                # Generate the left part of the method call string.
                # Method calls look like L/package1/package2/Class;->methodname(Param1Type,Param2Type);ReturnType
                call_string_left = 'L' + '/'.join(file.get_full_package().split('.')) + ';->'
                apkfile = apkdb.session.query(apkdb.File).filter(apkdb.File.id == file.hints[0]).first()
                call_replaces = {}
                method_replaces = {}
                done_methods = []
                for method in file.methods:
                    if not method.is_significant() or 'constructor ' in method.signature or 'abstract ' in method.signature:
                        continue
                    for hint in method.hints:
                        apkmethod = apkdb.session.query(apkdb.Method).filter(apkdb.Method.id == hint).first()
                        if apkmethod not in apkfile.methods or apkmethod.id in done_methods:
                            continue
                        done_methods.append(apkmethod.id)
                        to_search = self.method_call_name.match('.method '+method.signature).group(1)
                        method_name = self.method_name.match('.method '+method.signature).group(1)
                        new_method_name = self.method_name.match('.method '+apkmethod.signature).group(1)
                        # print('> Changing Method', method.signature, 'to', method.signature.replace(method_name + '(', new_method_name + '('))
                        # print('In', file.get_full_package())
                        method_replaces[method.signature] = \
                            method.signature.replace(method_name + '(', new_method_name + '(')
                        call_replaces[call_string_left + to_search] = \
                            call_string_left + to_search.replace(method_name + '(', new_method_name + '(')
                        break

                # Replace method definitions
                with open(file.get_full_path(), 'r') as f:
                    content = f.read()
                new_content = ''
                change = False
                for line in content.splitlines():
                    search = self.to_avoid.findall(line)
                    if len(search) == 0:
                        # Replace the old method definition with the new one.
                        # Method definitions look like: .method public static ... func_name(Param1Type, Param2Type);ReturnType
                        t = line
                        for from_replace, to_replace in method_replaces.items():
                            t = t.replace(from_replace, to_replace)
                        new_content += t
                    else:
                        new_content += line
                    if len(line) > 0:
                        new_content += os.linesep
                if not new_content == content:
                    change = True

                if change:
                    os.remove(file.get_full_path())
                    with open(file.get_full_path(), 'w+') as f:
                        f.write(new_content)

                # Replace method calls
                for r_file in eop.get_files():
                    with open(r_file.get_full_path(), 'r') as f:
                        content = f.read()
                    new_content = ''
                    change = False
                    for line in content.splitlines():
                        search = self.to_avoid.findall(line)
                        if len(search) == 0:
                            # Replace the old method call with the new one.
                            # Method calls look like
                            # L/package1/package2/Class;->methodname(Param1Type,Param2Type);ReturnType
                            t = line
                            for from_replace, to_replace in method_replaces.items():
                                t = t.replace(from_replace, to_replace)
                            new_content += t
                        else:
                            new_content += line
                        if len(line) > 0:
                            new_content += os.linesep
                    if not new_content == content:
                        change = True

                    if change:
                        os.remove(r_file.get_full_path())
                        with open(r_file.get_full_path(), 'w+') as f:
                            f.write(new_content)


# self.method_call_name = re.compile(r'\s*.method\s(?:.*)(\w\(.*\).*)')
#        self.method_name = re.compile(r'\s*.method\s(?:.*)(\w)\(.*\).*')
'''
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
'''
