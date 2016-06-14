import argparse
import os
import subprocess
from defusedxml import ElementTree
from api_counter import APICounter
from renamer import Renamer
from base import find_class_paths_and_iterate

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


def deobfuscate(path):
    android_manifest = ElementTree.parse(os.path.join(path, 'AndroidManifest.xml'))
    root = android_manifest.getroot()
    mains = search_mains(root)
    print('>> Main activities found:', mains)
    to_read = find_class_paths_and_iterate(path)
    if to_read is None:
        return
    api_counter = APICounter(threads, to_read)
    folded = api_counter.count(path)
    print(folded)
    # Renaming
    renamer = Renamer(to_read, path)
    renamer.rename(['a', 'b', 'c', 'd', 'e'], ['new1', 'new2', 'new3', 'new4', 'new5'])


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

    print('Rebuilding APK')
    run(['java', '-jar', 'apktool.jar', 'b', os.path.join(os.getcwd(), output_folder), '-o', apk_path+'_new.apk'])
    print('Don\'t forget to sign your apk with the following commands:')
    print('keytool -genkey -v -keystore my-release-key.keystore -alias alias_name -keyalg RSA -keysize 2048 -validity 10000')
    print('jarsigner -verbose -sigalg SHA1withRSA -digestalg SHA1 -keystore my-release-key.keystore my_application.apk alias_name')
    print('jarsigner -verify -verbose -certs my_application.apk')
    print('zipalign -v 4 your_project_name-unaligned.apk your_project_name.apk')


if __name__ == '__main__':
    main()
