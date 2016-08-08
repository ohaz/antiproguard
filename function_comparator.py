import re
import os
from pprint import pprint
import base

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
        self.database = base.database['function_comparator']
        self.COMPARE_LIMIT = 20

    def analyze_all(self):
        ptn = r'.method (.*)'
        pattern = re.compile(ptn)
        analyzed = []
        for work in self.to_read:
            analyzed.extend(self.analyze_file(work, pattern))
        return analyzed

    def analyze_all_in_package(self, package):
        ptn = r'.method (.*)'
        pattern = re.compile(ptn)
        analyzed = []
        for work in self.to_read:
            if work[2].startswith(package):
                analyzed.extend(self.analyze_file(work, pattern))
        return analyzed

    def analyze_file(self, work, pattern):
        analyzed = []
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

    def analyze_function_instruction_groups_content_ngram(self, content, function_signature, n):
        result_map = {key: 0 for key in instruction_groups}
        ptn = r'.method ' + re.escape(function_signature) + '\n((?:.*\r?\n)*?).end method'
        pattern = re.compile(ptn)

        lines = []

        for pt in pattern.findall(content):
            for line in pt.splitlines():
                line = line.strip()
                lines.append(line)
        for i, l in enumerate(lines):
            for key in instruction_groups:
                for instr in instruction_groups[key]:
                    if line.startswith(instr + ' '):
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
            new_analyzed[os.path.join(a['path'], a['file'])] = element
            if 'signature' in new_analyzed[os.path.join(a['path'], a['file'])]:
                del new_analyzed[os.path.join(a['path'], a['file'])]['signature']
        return new_analyzed

    def compare_to_db(self, analyzed):
        folders = {}
        vpaths = {}
        for data_key, data_value in self.database.items():
            folders_key = '.'.join((data_key.split('.'))[:-1])
            if folders_key not in folders:
                folders[folders_key] = {'found': {}, 'file_amount': 0, 'folder': ''}
            folders[folders_key]['file_amount'] += 1
            for k, v in analyzed.items():
                if self.compare_map(data_value['map'], v['result_map']):
                    if v['path'] not in folders[folders_key]['found']:
                        folders[folders_key]['found'][v['path']] = 0
                    folders[folders_key]['found'][v['path']] += 1
                    vpaths[v['path']] = vpaths.get(v['path'], 0) + 1
            highest = (None, -1)
            for found_key, found_value in folders[folders_key]['found'].items():
                if found_value > highest[1]:
                    highest = (found_key, found_value)
            folders[folders_key]['highest'] = {'path': highest[0], 'found': highest[1]}
        errors = self.calculate_errors(folders)
        pprint(vpaths)
        exit()
        return errors

    def calculate_errors(self, folders):
        result = {}
        for k, v in folders.items():
            error = 100 * abs(1 - ((v['highest']['found'] * 1.0) / (v['file_amount'] * 1.0)))
            result[k] = {'file_amount': v['file_amount'], 'found': v['highest']['found'], 'path': v['highest']['path'], 'error': error}
        return result

    def compare_map(self, map1, map2):
        result = True
        for k1, v1 in map1.items():
            if not v1 == map2[k1]:
                result = False

        if sum(map1.values()) < self.COMPARE_LIMIT:
            return False
        return result
