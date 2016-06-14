import argparse
import os
import subprocess
from defusedxml import ElementTree
from api_counter import APICounter

__author__ = 'ohaz'

threads = None


def run(cmd):
    subprocess.run(cmd)


def search_mains(xml_root):
    mains = []
    for application in xml_root:
        if application.tag == 'application':
            for activity in application:
                if activity.tag == 'activity':
                    for intent in activity:
                        if intent.tag == 'intent-filter':
                            for action in intent:
                                if action.tag == 'action':
                                    if 'android.intent.action.MAIN' in action.attrib.values():
                                        mains.append(
                                            activity.attrib['{http://schemas.android.com/apk/res/android}name'])
    return mains


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


def deobfuscate(path):
    android_manifest = ElementTree.parse(os.path.join(path, 'AndroidManifest.xml'))
    root = android_manifest.getroot()
    mains = search_mains(root)
    print('>> Main activities found:', mains)
    class_paths = find_class_paths(path)
    if len(class_paths) == 0:
        print('No smali files found :(')
        return
    print('Smali class folders found:', class_paths)
    to_read = []
    for folder in class_paths:
        to_read.extend(iterate_class(os.path.join(path, folder)))
    api_counter = APICounter(threads, to_read)
    folded = api_counter.count(path)
    print(folded)


def main():
    global threads
    parser = argparse.ArgumentParser(description='Deobfuscate Android Applications')
    parser.add_argument('apk', metavar='apk', type=str, help='The apk to unpack')
    parser.add_argument('-t', '--threads', dest='threads', action='store', nargs=1, type=int,
                        help='Maximum amount of threads used', default=4)
    args = parser.parse_args()

    output_folder = os.path.basename(args.apk)[:-4]
    apk_path = os.path.abspath(args.apk)
    threads = args.threads

    print('> Starting deobfuscation process for:', apk_path)
    print('---------------------------------------------')
    print()
    run(['java', '-jar', 'apktool.jar', 'd', apk_path])
    print('>> Decompiling to smali code done')
    deobfuscate(os.path.join(os.getcwd(), output_folder))


if __name__ == '__main__':
    main()
