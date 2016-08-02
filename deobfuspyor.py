import argparse
import os
import subprocess
from defusedxml import ElementTree
from api_counter import APICounter
from analyzer import Analyzer
from function_comparator import FunctionComparator
from renamer import Renamer
from base import find_class_paths_and_iterate
import base
import shutil
import colorama
from colorama import Fore, Style
from pprint import pprint
import json
import database

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
    folded = api_counter.count_and_compare(path)
    shortened = api_counter.shortened
    api_counter_compared = api_counter.compared
    # Renaming
    renamer = Renamer(to_read, path)
    # renamer.rename_package(['a', 'b', 'c', 'd', 'e'], ['new1', 'new2', 'new3', 'new4', 'new5'])
    # renamer.rename_function(['new1', 'new2', 'new3', 'new4', 'new5'], 'A', 'b', 'newname')

    comparator = FunctionComparator(threads, to_read)
    result_map = comparator.analyze_all()
    folded_map = comparator.fold_by_file(result_map)
    function_comparator_compared = comparator.compare_to_db(folded_map)
    analyzer = Analyzer()
    analyzer.analyze(api_counter_compared, function_comparator_compared)

    # signature = comparator.create_function_signature('public', '', 'b', 'Ljava/lang/String;', 'Ljava/lang/String;')
    # comparator.analyze_function_instruction_groups(path, os.path.join('smali', 'a', 'b', 'c', 'd', 'e', 'A.smali'), signature)


def analyze(path):
    android_manifest = ElementTree.parse(os.path.join(path, 'AndroidManifest.xml'))
    root = android_manifest.getroot()
    mains = search_mains(root)
    print('>> Main activities found:', mains)
    to_read = find_class_paths_and_iterate(path)
    if to_read is None:
        return

    #package_to_analyze = input('Name of the Package to analyze (divided by .):')
    #package_to_analyze = package_to_analyze.replace('.', os.sep)

    packages_to_search = ['org.bouncycastle', 'net.java.otr4j.crypto', 'org.sqlite', 'android.support.v4', 'android.support.v7', 'android.support.v13']
    packages_to_search = [x.split('.') for x in packages_to_search]

    api_counter = APICounter(threads, to_read)
    folded = api_counter.count(path)
    shortened = api_counter.shortened
    already_in_db = []
    for package in packages_to_search:
        current = shortened
        for e in package:
            if e in current:
                current = current[e]
            else: break
        else:
            # Searched for a package and found it!
            lib = database.session.query(database.Library).filter(database.Library.base_package == '.'.join(package)).first()
            if not lib:
                lib = database.Library(name='.'.join(package), base_package='.'.join(package))
                database.session.add(lib)
            in_db = False
            for version in lib.versions:
                if version.api_calls == current['.overall']:
                    print('Already in DB:', lib, version)
                    already_in_db.append((str(lib), str(version)))
                    in_db = True
            if not in_db:
                version = database.LibraryVersion(library=lib, api_calls=current['.overall'])
                database.session.add(version)
        database.session.commit()
    return already_in_db




    #comparator = FunctionComparator(threads, to_read)
    #result_map = comparator.analyze_all_in_package(package_to_analyze)
    #folded_map = comparator.fold_by_file(result_map)
    #for k, v in folded_map.items():
    #    package = v['path'].replace(os.sep, '.')
    #    jclass = v['file'][:-6]
    #    if package+'.'+jclass not in base.database['function_comparator']:
    #        base.database['function_comparator'][package+'.'+jclass] = {
    #            'map': v['result_map'],
    #            'package': package,
    #            'class': jclass
    #        }


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

    apk_paths = os.path.abspath(args.apk)
    threads = args.threads
    if isinstance(threads, list):
        threads = threads[0]
    args.skip_decompile = True if args.skip_all else args.skip_decompile
    args.skip_build = True if args.skip_all else args.skip_build

    # print(Fore.LIGHTGREEN_EX+' Reading config file / database')
    # with open('database.json', 'r') as f:
    #     base.database = json.load(f)

    if os.path.isdir(apk_paths):
        apks = [os.path.join(apk_paths, x) for x in os.listdir(apk_paths) if x.endswith('.apk')]
    else:
        apks = [apk_paths]

    base.verbose = args.verbose
    already_in_db = []
    for apk in apks:
        output_folder = os.path.basename(apk)[:-4]

        print(Fore.GREEN+'> Starting deobfuscation process for:', apk)
        print('---------------------------------------------')
        print(Style.RESET_ALL)
        if not args.keep and os.path.exists(output_folder):
            print(Fore.RED+'>> Removing old output folder')
            print(Style.RESET_ALL)
            shutil.rmtree(output_folder)
        if not args.skip_decompile:
            run(['java', '-jar', 'apktool.jar', 'd', apk])
            print(Fore.BLUE+'>> Decompiling to smali code done')
        print(Style.RESET_ALL)
        if not args.analyze:
            deobfuscate(os.path.join(os.getcwd(), output_folder))
            print(Fore.GREEN+'---------------------------------------------')
            print('Done deobfuscating...'+Style.RESET_ALL)
            if not args.skip_build:
                print('Rebuilding APK')
                run(['java', '-jar', 'apktool.jar', 'b', os.path.join(os.getcwd(), output_folder), '-o', apk+'_new.apk'])
                if args.verbose:
                    base.verbose = True
                    print(Fore.LIGHTRED_EX+'---------------------------------------------')
                    print('Don\'t forget to sign your apk with the following commands:')
                    print('keytool -genkey -v -keystore my-release-key.keystore -alias alias_name -keyalg RSA -keysize 2048 -validity 10000')
                    print('jarsigner -verbose -sigalg SHA1withRSA -digestalg SHA1 -keystore my-release-key.keystore my_application.apk alias_name')
                    print('jarsigner -verify -verbose -certs my_application.apk')
                    print('zipalign -v 4 your_project_name-unaligned.apk your_project_name.apk')
        else:
            already_in_db.extend(analyze(os.path.join(os.getcwd(), output_folder)))

            # os.remove('database.json')
            # with open('database.json', 'a+') as f:
            #    json.dump(base.database, f, indent=2)

        if not args.keep and os.path.exists(output_folder):
            print(Fore.RED+'>> Removing output folder')
            print(Style.RESET_ALL)
            shutil.rmtree(output_folder)
    if args.analyze:
        print(Fore.GREEN)
        pprint(already_in_db)
        print(Style.RESET_ALL)

if __name__ == '__main__':
    main()
