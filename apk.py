import os
from pprint import pprint
import base
import re

__author__ = 'ohaz'

instruction_groups = {
    'neg-int': 'CN',
    'not-int': 'CN',
    'neg-long': 'CN',
    'not-long': 'CN',
    'neg-float': 'CN',
    'neg-double': 'CN',
    'int-to-long': 'CN',
    'int-to-float': 'CN',
    'int-to-double': 'CN',
    'long-to-int': 'CN',
    'long-to-float': 'CN',
    'long-to-double': 'CN',
    'float-to-int': 'CN',
    'float-to-long': 'CN',
    'float-to-double': 'CN',
    'double-to-int': 'CN',
    'double-to-long': 'CN',
    'double-to-float': 'CN',
    'int-to-byte': 'CN',
    'int-to-char': 'CN',
    'int-to-short': 'CN',
    'add-int': 'MT',
    'sub-int': 'MT',
    'mul-int': 'MT',
    'div-int': 'MT',
    'rem-int': 'MT',
    'and-int': 'MT',
    'or-int': 'MT',
    'xor-int': 'MT',
    'shl-int': 'MT',
    'shr-int': 'MT',
    'ushr-int': 'MT',
    'add-long': 'MT',
    'sub-long': 'MT',
    'mul-long': 'MT',
    'div-long': 'MT',
    'rem-long': 'MT',
    'and-long': 'MT',
    'or-long': 'MT',
    'xor-long': 'MT',
    'shl-long': 'MT',
    'shr-long': 'MT',
    'ushr-long': 'MT',
    'add-float': 'MT',
    'sub-float': 'MT',
    'mul-float': 'MT',
    'div-float': 'MT',
    'rem-float': 'MT',
    'add-double': 'MT',
    'sub-double': 'MT',
    'mul-double': 'MT',
    'div-double': 'MT',
    'rem-double': 'MT',
    'invoke-virtual': 'IN',
    'invoke-super': 'IN',
    'invoke-direct': 'IN',
    'invoke-static': 'IN',
    'invoke-interface': 'IN',
    'invoke-interface-range': 'IN',
    'invoke-direct-empty': 'IN',
    'execute-inline': 'IN',
    'invoke-virtual-quick': 'IN',
    'invoke-super-quick': 'IN',
    'sget': 'SF',
    'sget-wide': 'SF',
    'sget-object': 'SF',
    'sget-boolean': 'SF',
    'sget-byte': 'SF',
    'sget-char': 'SF',
    'sget-short': 'SF',
    'sput': 'SF',
    'sput-wide': 'SF',
    'sput-object': 'SF',
    'sput-boolean': 'SF',
    'sput-byte': 'SF',
    'sput-char': 'SF',
    'sput-short': 'SF',
    'iget': 'IF',
    'iget-wide': 'IF',
    'iget-object': 'IF',
    'iget-boolean': 'IF',
    'iget-byte': 'IF',
    'iget-char': 'IF',
    'iget-short': 'IF',
    'iput': 'IF',
    'iput-wide': 'IF',
    'iput-object': 'IF',
    'iput-boolean': 'IF',
    'iput-byte': 'IF',
    'iput-char': 'IF',
    'iput-short': 'IF',
    'iget-wide-quick': 'IF',
    'iget-object-quick': 'IF',
    'iput-quick': 'IF',
    'iput-wide-quick': 'IF',
    'iput-object-quick': 'IF',
    'cmpl-float': 'CP',
    'cmpg-float': 'CP',
    'cmpl-double': 'CP',
    'cmpg-double': 'CP',
    'cmp-long': 'CP',
    'if-eq': 'CP',
    'if-ne': 'CP',
    'if-lt': 'CP',
    'if-ge': 'CP',
    'if-gt': 'CP',
    'if-le': 'CP',
    'if-eqz': 'CP',
    'if-nez': 'CP',
    'if-ltz': 'CP',
    'if-gez': 'CP',
    'if-gtz': 'CP',
    'if-lez': 'CP',
    'goto': 'GO',
    'throw': 'GO',
    'array-length': 'AR',
    'new-array': 'AR',
    'filled-new-array': 'AR',
    'filled-new-array-range': 'AR',
    'fill-array-data': 'AR',
    'aget': 'AR',
    'aget-wide': 'AR',
    'aget-object': 'AR',
    'aget-boolean': 'AR',
    'aget-byte': 'AR',
    'aget-char': 'AR',
    'aget-short': 'AR',
    'aput': 'AR',
    'aput-wide': 'AR',
    'aput-object': 'AR',
    'aput-boolean': 'AR',
    'aput-byte': 'AR',
    'aput-char': 'AR',
    'aput-short': 'AR',
    'check-cast': 'IO',
    'instance-of': 'IO',
    'new-instance': 'IO',
    'monitor-enter': 'MN',
    'monitor-exit': 'MN',
    'const': 'CO',
    'const-wide': 'CO',
    'const-string': 'CO',
    'const-string-jumbo': 'CO',
    'const-class': 'CO',
    'return-void': 'RT',
    'return': 'RT',
    'return-wide': 'RT',
    'return-object': 'RT',
    'move': 'MV',
    'move-wide': 'MV',
    'move-object': 'MV',
    'move-result': 'MV',
    'move-result-object': 'MV',
    'move-exception': 'MV'
}


class Package:

    def __init__(self, name, parent=None, special=False):
        """
        Init Method for a java package folder
        :param name: the name of the folder/package
        :param parent: the parent folder/package
        :param special: used to show non-java related folders, e.g. smali and root
        """
        self.dot_id = base.dot_id_counter
        base.dot_id_counter += 1
        self.name = name
        self.parent = parent
        self.child_packages = []
        self.child_files = []
        self.special = special
        self._special_path = ''
        self.is_eop = False

    def iterate_end_of_packages(self):
        """
        Finds the first package that contains a file
        :return: void
        """
        if len(self.child_files) > 0:
            self.is_eop = True
            return
        for child in self.child_packages:
            child.iterate_end_of_packages()

    def get_files(self):
        """
        Gets all files in this package and all its sub packages
        :return: a list of File objects
        """
        files = []
        files.extend(self.child_files)
        for child in self.child_packages:
            files.extend(child.get_files())
        return files

    def set_special_path(self, path):
        """
        Set a special path, e.g. for smali or root "Packages"
        :param path: the special path
        :return: void
        """
        if not self.special:
            raise Exception('NOT SPECIAL')
        self._special_path = path

    def add_child_file(self, child):
        """
        Appends a child File object to the list of file children
        :param child: a File object
        :return: void
        """
        self.child_files.append(child)

    def add_child_package(self, child):
        """
        Appends a child Package object to the list of package children
        :param child: a Package object
        :return: void
        """
        self.child_packages.append(child)

    def is_obfuscated(self):
        """
        Tests via package name length if this package may be obfuscated.
        package names with 1 or 2 characters length are considered obfuscated
        :return: a float that shows how high the chance for this package to be obfuscated is
        """
        package = self.get_full_package()
        packages = package.split('.')
        shorter = 0
        really_long = 0
        for p in packages:
            if len(p) < 3:
                shorter += 1
            elif len(p) > 4:
                really_long += 1
        if really_long > (0.5 * len(packages)):
            shorter = max(0,shorter-really_long)
        return shorter*1.0 / (len(packages)*1.0)

    def get_full_path(self):
        """
        Get the full path in the filesystem, to make opening files for reading/writing easier
        :return: the full path to the file
        """
        if self.special:
            return self._special_path
        else:
            return os.path.join(self.parent.get_full_path(), self.name)

    def get_path(self):
        """
        Get the internal path to the package
        :return: the path including all not-special parents
        """
        if self.special:  # May need if self.parent.special
            return ''
        else:
            return os.path.join(self.parent.get_path(), self.name)

    def get_full_package(self):
        """
        Java-like path/package presentation, using dots instead of os separators
        :return: dot-style path representation
        """
        parent = ''
        if not self.parent.special:
            parent = self.parent.get_full_package() + '.'
        return parent + self.name

    def pprint(self):
        """
        Prettyprints this package and all sub packages
        :return: void
        """
        print('Package:')
        pprint(self.name)
        pprint(self.child_packages)
        pprint(self.child_files)
        for p in self.child_packages:
            p.pprint()
        for f in self.child_files:
            f.pprint()

    def graph(self, dot, p, root=False, include_files=False):
        """
        Make a dot graph of this package
        :param dot: the dot graph
        :param p: the parent
        :param root: boolean flag to know whether this node is the root node
        :param include_files: boolean flag whether files should be included
        :return: void
        """
        dot.node(str(self.dot_id), 'P: ' + self.name)
        if not root:
            dot.edge(str(p.dot_id), str(self.dot_id))
        for p in self.child_packages:
            p.graph(dot, self)
        if include_files:
            for f in self.child_files:
                f.graph(dot, self)


class File:

    def __init__(self, name, parent):
        """
        Class representing a Smali Code File
        :param name: the Name of the file
        :param parent: The package the file is in
        """
        self.name = name
        self.parent = parent
        self.dot_id = base.dot_id_counter
        base.dot_id_counter += 1
        self.function_pattern = re.compile(r'\.method (.*)\n((?:.*\r?\n)*?)\.end method')
        self.methods = []

    def get_path(self):
        """
        Get the internal path to the file
        :return: the path including all not-special parents
        """
        return os.path.join(self.parent.get_path(), self.name)

    def get_full_path(self):
        """
        Get the full path in the filesystem, to make opening files for reading/writing easier
        :return: the full path to the file
        """
        return os.path.join(self.parent.get_full_path(), self.name)

    def get_class_name(self):
        """
        Gets the name of the class, usually filename -5 characters (for .smali)
        This may have to be fixed in the future, by reading out the actual name of the class
        :return: A string containing the Classname
        """
        return self.name[:-6]

    def get_full_package(self):
        """
        Java-like path/package presentation, using dots instead of os separators
        :return: dot-style path representation
        """
        return '.'.join([self.parent.get_full_package(), self.get_class_name()])

    def is_obfuscated(self):
        """
        Tests via package name length if the package this file is in may be obfuscated.
        package names with 1 or 2 characters length are considered obfuscated
        :return: a float that shows how high the chance for this package to be obfuscated is
        """
        return self.parent.is_obfuscated()

    def generate_methods(self):
        """
        Reads out all methods from the smali file
        :return: a list of method objects
        """
        with open(self.get_full_path(), 'r') as f:
            content = f.read()
        for method in self.function_pattern.findall(content):
            self.methods.append(Method(self, method[0], method[1]))

        return self.methods

    def generate_basic_blocks(self):
        """
        Generates the basic block structures for all methods in this file
        :return: void
        """
        methods = self.methods
        if len(methods) == 0:
            methods = self.generate_methods()
        for method in methods:
            method.generate_basic_blocks()

    def generate_ngrams(self, n=2, intersect=True):
        """
        Generates the n-grams for all methods in this file
        :param n: the length of a gram
        :param intersect: indicates whether n-grams should have intersections (ABCD -> AB, BC, CD or AB, CD)
        :return: void
        """
        methods = self.methods
        if len(methods) == 0:
            methods = self.generate_methods()
        for method in methods:
            method.generate_ngrams(n, intersect)

    def pprint(self):
        """
        Prettyprints the file
        :return: void
        """
        print('File:')
        pprint(self.name)
        pprint(self.parent)

    def graph(self, dot, p):
        """
        Make a dot graph of this file
        :param dot: the dot graph
        :param p: the parent
        :return: void
        """
        dot.node(str(self.dot_id), 'F: ' + self.name)
        dot.edge(str(p.dot_id), str(self.dot_id))


class Method:

    def __init__(self, file, signature, instructions):
        """
        Representation of a method
        :param file: the file this method is in
        :param signature: the signature of this method
        :param instructions: the bytecode/smali instructions in this method
        """
        self.file = file
        self.signature = signature
        self.instructions = instructions
        self.basic_blocks = []
        self.ngrams = []

    def instr_stripped_gen(self):
        """
        generator for stripped down instructions
        :return: a list of instructions without empty lines and leading spaces
        """
        yield from [x.strip() for x in self.instructions.splitlines() if len(x.strip()) > 0]

    instr_stripped = property(instr_stripped_gen)

    def pprint(self):
        """
        Prettyprints this method
        :return: void
        """
        print(self.signature, 'in', self.file.name)

    def generate_ngrams(self, n=2, intersect=True):
        """
        Generates n-grams for this method.
        :param n: the length of a gram
        :param intersect: indicates whether n-grams should have intersections (ABCD -> AB, BC, CD or AB, CD)
        :return: void
        """
        print('METHOD', self.signature, 'in class', self.file.name)
        in_work = []
        i = 0
        for instr in self.instr_stripped:
            found = False
            for k in instruction_groups:
                if instr.startswith(k):
                    found = True
            if not found:
                if not instr.startswith('.') and not instr.startswith('0x') and not instr.startswith(':'):
                    print(instr)
                continue
            if intersect:
                in_work.append(list())
            elif i % n == 0:
                in_work.append(list())
            i += 1
            if len(in_work[0]) >= n:
                self.ngrams.append(tuple(in_work.pop(0)))
            for k, v in instruction_groups.items():
                if instr.startswith(k+' ') or instr.startswith(k+'/') or instr == k:
                    for ngram in in_work:
                        ngram.append(v)
                    break
            else:
                print(instr)

        print(self.ngrams)

    def generate_basic_blocks(self):
        """
        Generates the basic block structures for this method.
        :return: void
        """
        enders = ['GO', 'RT', 'invoke-', 'if-']
        starters = [':', '.catch']
        entry = 0
        splits = self.instructions.splitlines()
        prev = None
        for key, instr in enumerate(splits):
            i = instr.strip()
            for e in enders:
                if i.startswith(e):
                    bb = BasicBlock.new_block(self, splits[entry:key+1], prev)
                    if bb:
                        self.basic_blocks.append(bb)
                    entry = key+1
                    if prev:
                        prev.next = bb
                    prev = bb
            for s in starters:
                if i.startswith(s):
                    if key != entry:
                        if entry < key:
                            bb = BasicBlock.new_block(self, splits[entry:key], prev)
                            if bb:
                                self.basic_blocks.append(bb)
                            entry = key
                            if prev:
                                prev.next = bb
                            prev = bb
        if entry != len(splits):
            bb = BasicBlock(self, splits[entry:], prev)
            if prev:
                prev.next = bb
            self.basic_blocks.append(bb)

        self.basic_blocks[-1].last = True
        self.build_cfg()

    def build_cfg(self):
        """
        Build a CFG using the BasicBlocks
        :return: void
        """
        for block in self.basic_blocks:
            if not block.ends_unconditional():
                if block.next:
                    block.next.parents.append(block)
                    block.children.append(block.next)
            targets = block.get_targets()
            if len(targets) > 0:
                for b in self.basic_blocks:
                    starters = b.get_start_markers()
                    for t in targets:
                        if t in starters:
                            b.parents.append(block)
                            block.children.append(b)
                            break
        if 'onOptionsItemSelected' in self.signature and 'MainActivity' in self.file.name:
            from graphviz import Digraph
            dot = Digraph()
            self.basic_blocks[0].graph(dot, done=[])
            # dot.render('OUT.png', view=True)
            with open('cfg.dot', 'w+') as f:
                f.write(dot.source)


class BasicBlock:

    def __init__(self, method, instructions, prev_bb, next_bb=None, parents=None, children=None):
        """
        Representation of a basic block.
        :param method: The method this BB belongs to
        :param instructions: The instructions included in this BB
        :param prev_bb: The basic block that is in front of this BB in the code
        :param next_bb: The basic block that is behind this BB in the code
        :param parents: The CFG parents of this block
        :param children: The CFG children of this block
        """
        self.method = method
        self.prev = prev_bb
        self.next = next_bb
        self.dot_id = base.dot_id_counter
        base.dot_id_counter += 1
        self.instructions = [x for x in instructions if len(x.strip()) != 0]
        self.parents = parents if parents is not None else []
        self.children = children if children is not None else []
        self.last = False

    def graph(self, dot, done=None):
        """
        Make a dot graph of this BasicBlock and all its children
        :param dot: the dot graph
        :param done: a list of blcoks already visited
        :return: void
        """
        if done is None:
            done = []
        if self.dot_id not in done:
            dot.node(str(self.dot_id), 'F: ' + str(self.instructions))
            for c in self.children:
                dot.edge(str(self.dot_id), str(c.dot_id))
                c.graph(dot, done+[self.dot_id])

    def pprint(self):
        """
        Pretty Prints this Basic block
        :return: void
        """
        print(self.parents, self.children)
        pprint(self.instructions)

    def ends_unconditional(self):
        """
        Checks if this block ends with an unconditional jump
        :return: boolean that shows if this block ends with an unconditional jump
        """
        ll = self.instructions[-1].strip()
        if ll.startswith('GO') or ll.startswith('return') or self.last:
            return True
        return False

    def get_start_markers(self):
        """
        Returns a list of all markers that can start this block.
        Should always be a list with only 1 element, otherwise something went horribly wrong
        :return: a list of markers
        """
        starters = []
        for instr in self.instructions:
            i = instr.strip()
            if i.startswith(':'):
                starters.append(i)
        return starters

    def get_targets(self):
        """
        Returns a list of all targets this basic blocks can jump to.
        Should always be a list with only 1 element, otherwise something went horribly wrong
        :return: a list of targets
        """
        targets = []
        goto_target = re.compile(r'goto\s(.*)')
        if_target = re.compile(r'if-\w+\s.*,\s(\S*)')
        # TODO: What about catch?
        ll = self.instructions[-1].strip()
        goto_match = goto_target.match(ll)
        if goto_match:
            targets.append(goto_match.group(1))
        if_match = if_target.match(ll)
        if if_match:
            targets.append(if_match.group(1))
        return targets

    @classmethod
    def new_block(cls, method, instructions, prev_bb, next_bb=None, parents=None, children=None):
        """
        Creates a new block only if the amount of instructions is at least 1.
        This is used as a convenience function to make creating the BBs easier
        :param method: The method this BB belongs to
        :param instructions: The instructions included in this BB
        :param prev_bb: The basic block that is in front of this BB in the code
        :param next_bb: The basic block that is behind this BB in the code
        :param parents: The CFG parents of this block
        :param children: The CFG children of this block
        :return:
        """
        obj = cls(method, instructions, prev_bb, next_bb, parents, children)
        if len(obj.instructions) >= 1:
            return obj
        return None
