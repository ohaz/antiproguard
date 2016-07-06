import argparse
import os
import subprocess
from defusedxml import ElementTree
from api_counter import APICounter
from function_comparator import FunctionComparator
from renamer import Renamer
from base import find_class_paths_and_iterate
import base
import shutil
import colorama
from colorama import Fore, Style
from pprint import pprint

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
    # TODO ENABLE COUNTING AGAIN
    # folded = api_counter.count_and_compare(path)
    # Renaming
    renamer = Renamer(to_read, path)
    # renamer.rename_package(['a', 'b', 'c', 'd', 'e'], ['new1', 'new2', 'new3', 'new4', 'new5'])
    # renamer.rename_function(['new1', 'new2', 'new3', 'new4', 'new5'], 'A', 'b', 'newname')

    comparator = FunctionComparator(threads, to_read)
    result_map = comparator.analyze_all()
    for result in result_map:
        if sum(result['result_map'].values()) > 20:
            print(result)
    signature = comparator.create_function_signature('public', '', 'b', 'Ljava/lang/String;', 'Ljava/lang/String;')
    # comparator.analyze_function_instruction_groups(path, os.path.join('smali', 'a', 'b', 'c', 'd', 'e', 'A.smali'), signature)


def analyze(path):
    android_manifest = ElementTree.parse(os.path.join(path, 'AndroidManifest.xml'))
    root = android_manifest.getroot()
    mains = search_mains(root)
    print('>> Main activities found:', mains)
    to_read = find_class_paths_and_iterate(path)
    if to_read is None:
        return

    #api_counter = APICounter(threads, to_read)
    #folded = api_counter.count(path)
    #shortened = api_counter.shortened
    package_to_analyze = input('Name of the Package to analyze (divided by .):')
    package_to_analyze = package_to_analyze.replace('.', os.sep)

    comparator = FunctionComparator(threads, to_read)
    result_map = comparator.analyze_all_in_package(package_to_analyze)
    comparator.fold_by_file(result_map)
    #for result in result_map:
    #    pprint(result)
        #if sum(result['result_map'].values()) > 20:
        #    print(result)


def main():
    global threads
    parser = argparse.ArgumentParser(description='Deobfuscate Android Applications')
    parser.add_argument('apk', metavar='apk', type=str, help='The apk to unpack')
    parser.add_argument('-t', '--threads', dest='threads', action='store', nargs=1, type=int,
                        help='Maximum amount of threads used', default=4)
    parser.add_argument('-v', '--verbose', dest='verbose', action='store_true', help='Show more detailed information')
    parser.add_argument('-k', '--keep', dest='keep', action='store_true', help='Keep old folder')
    parser.add_argument('-sd', '--skip-decompile', dest='skip_decompile', action='store_true', help='Skip decompilation')
    parser.add_argument('-sb', '--skip-build', dest='skip_build', action='store_true', help='Skip recompilation / rebuilding apk')
    parser.add_argument('-s', '--skip', dest='skip_all', action='store_true', help='Skip all')
    parser.add_argument('-a', '--analyze', dest='analyze', action='store_true', help='Analyze instead of deobfuscate. With this, you can add new stuff to the database.')
    args = parser.parse_args()

    colorama.init()

    output_folder = os.path.basename(args.apk)[:-4]
    apk_path = os.path.abspath(args.apk)
    threads = args.threads
    if isinstance(threads, list):
        threads = threads[0]
    args.skip_decompile = True if args.skip_all else args.skip_decompile
    args.skip_build = True if args.skip_all else args.skip_build

    print(Fore.GREEN+'> Starting deobfuscation process for:', apk_path)
    print('---------------------------------------------')
    print(Style.RESET_ALL)
    if not args.keep and os.path.exists(output_folder):
        print(Fore.RED+'>> Removing old output folder')
        print(Style.RESET_ALL)
        shutil.rmtree(output_folder)
    if not args.skip_decompile:
        run(['java', '-jar', 'apktool.jar', 'd', apk_path])
        print(Fore.BLUE+'>> Decompiling to smali code done')
    print(Style.RESET_ALL)
    if not args.analyze:
        deobfuscate(os.path.join(os.getcwd(), output_folder))
        print(Fore.GREEN+'---------------------------------------------')
        print('Done deobfuscating...'+Style.RESET_ALL)
        if not args.skip_build:
            print('Rebuilding APK')
            run(['java', '-jar', 'apktool.jar', 'b', os.path.join(os.getcwd(), output_folder), '-o', apk_path+'_new.apk'])
            if args.verbose:
                base.verbose = True
                print(Fore.LIGHTRED_EX+'---------------------------------------------')
                print('Don\'t forget to sign your apk with the following commands:')
                print('keytool -genkey -v -keystore my-release-key.keystore -alias alias_name -keyalg RSA -keysize 2048 -validity 10000')
                print('jarsigner -verbose -sigalg SHA1withRSA -digestalg SHA1 -keystore my-release-key.keystore my_application.apk alias_name')
                print('jarsigner -verify -verbose -certs my_application.apk')
                print('zipalign -v 4 your_project_name-unaligned.apk your_project_name.apk')
    else:
        analyze(os.path.join(os.getcwd(), output_folder))


if __name__ == '__main__':
    main()
