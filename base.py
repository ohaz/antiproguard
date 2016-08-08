import os

__author__ = 'ohaz'

verbose = False

database = None

dot_id_counter = 0


def find_class_paths(path):
    class_paths = []
    for f in os.listdir(path):
        if 'smali' in f:
            class_paths.append(f)
    return class_paths


def iterate_class(path, start=''):
    to_iterate = []
    to_read = []
    for f in os.listdir(path):
        if os.path.isdir(os.path.join(path, f)):
            to_iterate.append(os.path.join(path, f))
        else:
            to_read.append((path, f, start))

    for folder in to_iterate:
        to_read.extend(iterate_class(folder, os.path.join(start, os.path.basename(folder))))
    return to_read


def find_class_paths_and_iterate(path):
    to_read = []
    class_paths = find_class_paths(path)
    if len(class_paths) == 0:
        print('No smali files found :(')
        return None
    print('Smali class folders found:', class_paths)
    for folder in class_paths:
        to_read.extend(iterate_class(os.path.join(path, folder)))
    return to_read
