import re
import os
from concurrent.futures import ThreadPoolExecutor
from pprint import pprint

__author__ = 'ohaz'


instruction_groups = {

    'move': [
        'move',
        'move-wide',
        'move-object',
        'move-result',
        'move-result-object',
        'move-exception'
    ],
    'return': [
        'return-void',
        'return',
        'return-wide',
        'return-object'
    ],
    'const': [
        'const',
        'const-wide',
        'const-string',
        'const-string-jumbo',
        'const-class'
    ],
    'monitor': [
        'monitor-enter',
        'monitor-exit'
    ],
    'instance': [
        'check-cast',
        'instance-of'
    ],
    'array': [
        'array-length',
        'new_array',
        'filled-new-array',
        'filled-new-array-range',
        'fill-array-data',
        'aget',
        'aget-wide',
        'aget-object',
        'aget-boolean',
        'aget-byte',
        'aget-char',
        'aget-short',
        'aput',
        'aput-wide',
        'aput-object',
        'aput-boolean',
        'aput-byte',
        'aput-char',
        'aput-short'
    ],
    'goto': [
        'goto',
        'throw'
    ],
    'cmp': [
        'cmpl-float',
        'cmpg-float',
        'cmpl-double',
        'cmpg-double',
        'cmp-long',
        'if-eq',
        'if-ne',
        'if-lt',
        'if-ge',
        'if-gt',
        'if-le',
        'if-eqz',
        'if-nez',
        'if-ltz',
        'if-gez',
        'if-gtz',
        'if-lez'
    ],
    'instance-field': [
        'iget',
        'iget-wide',
        'iget-object',
        'iget-boolean',
        'iget-byte',
        'iget-char',
        'iget-short',
        'iput',
        'iput-wide',
        'iput-object',
        'iput-boolean',
        'iput-byte',
        'iput-char',
        'iput-short',
        'iget-wide-quick',
        'iget-object-quick',
        'iput-quick',
        'iput-wide-quick',
        'iput-object-quick',
    ],
    'static-field': [  # Maybe merge with instance field?
        'sget',
        'sget-wide',
        'sget-object',
        'sget-boolean',
        'sget-byte',
        'sget-char',
        'sget-short',
        'sput',
        'sput-wide',
        'sput-object',
        'sput-boolean',
        'sput-byte',
        'sput-char',
        'sput-short'
    ],
    'invoke': [
        'invoke-virtual',
        'invoke-super',
        'invoke-direct',
        'invoke-static',
        'invoke-interface',
        'invoke-interface-range',
        'invoke-direct-empty',
        'execute-inline',
        'invoke-virtual-quick',
        'invoke-super-quick',
    ],
    'math': [
        'neg-int',
        'not-int',
        'neg-long',
        'not-long',
        'neg-float',
        'neg-double',
        'int-to-long',
        'int-to-float',
        'int-to-double',
        'long-to-int',
        'long-to-float',
        'long-to-double',
        'float-to-int',
        'float-to-long',
        'float-to-double',
        'double-to-int',
        'double-to-long',
        'double-to-float',
        'int-to-byte',
        'int-to-char',
        'int-to-short',
        'add-int',
        'sub-int',
        'mul-int',
        'div-int',
        'rem-int',
        'and-int',
        'or-int',
        'xor-int',
        'shl-int',
        'shr-int',
        'ushr-int',
        'add-long',
        'sub-long',
        'mul-long',
        'div-long',
        'rem-long',
        'and-long',
        'or-long',
        'xor-long',
        'shl-long',
        'shr-long',
        'ushr-long',
        'add-float',
        'sub-float',
        'mul-float',
        'div-float',
        'rem-float',
        'add-double',
        'sub-double',
        'mul-double',
        'div-double',
        'rem-double',
    ]
}


class FunctionComparator:

    def __init__(self, threads, to_read):
        self.to_read = to_read
        self.threads = threads

    def analyze_all(self):
        ptn = r'.method (.*)'
        pattern = re.compile(ptn)
        analyzed = []
        for work in self.to_read:
            with open(os.path.join(work[0], work[1]), 'r') as file:
                content = file.read()
                for fct_signature in pattern.findall(content):
                    analyzed.append({'signature': fct_signature, 'file': work[1], 'path': work[2],
                                     'result_map':
                                         self.analyze_function_instruction_groups_content(content, fct_signature)})
        return analyzed

    def analyze_all_in_package(self, package):
        ptn = r'.method (.*)'
        pattern = re.compile(ptn)
        analyzed = []
        for work in self.to_read:
            if work[2].startswith(package):
                with open(os.path.join(work[0], work[1]), 'r') as file:
                    content = file.read()
                    for fct_signature in pattern.findall(content):
                        analyzed.append({'signature': fct_signature, 'file': work[1], 'path': work[2],
                                         'result_map':
                                             self.analyze_function_instruction_groups_content(content, fct_signature)})
        return analyzed

    def create_function_signature(self, visibility, static, name, params, return_type):
        if not static == '':
            static += ' '
        return '{} {}{}\({}\){}'.format(visibility, static, name, params, return_type)

    def analyze_function_instruction_groups(self, basepath, path, function_signature):
        with open(os.path.join(basepath, path), 'r') as f:
            content = f.read()
            self.analyze_function_instruction_groups_content(content, function_signature)

    def analyze_function_instruction_groups_content(self, content, function_signature):
        result_map = {key: 0 for key in instruction_groups}
        ptn = r'.method '+re.escape(function_signature)+'\n((?:.*\r?\n)*?).end method'
        pattern = re.compile(ptn)

        for pt in pattern.findall(content):
            for line in pt.splitlines():
                line = line.strip()
                for key in instruction_groups:
                    for instr in instruction_groups[key]:
                        if line.startswith(instr+' '):
                            result_map[key] += 1
        return result_map

    def fold_by_file(self, analyzed):
        new_analyzed = {}
        for a in analyzed:
            element = new_analyzed.get(os.path.join(a['path'], a['file']))
            if element:
                for k, v in a['result_map'].items():
                    element['result_map'][k] += v
            else:
                element = a
                del element['signature']
            new_analyzed[os.path.join(a['path'], a['file'])] = element
        pprint(new_analyzed)
