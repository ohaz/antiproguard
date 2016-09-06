import argparse
import os
import subprocess
from defusedxml import ElementTree
from api_counter import APICounter
from analyzer import Analyzer
from function_comparator import FunctionComparator
from renamer import Renamer
from base import find_class_paths_and_iterate, find_class_paths
import base
import shutil
import colorama
from colorama import Fore, Style
from pprint import pprint
import database
from apk import File, Package
import apkdb
from elsim import SimHash

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

    # package_to_analyze = input('Name of the Package to analyze (divided by .):')
    # package_to_analyze = package_to_analyze.replace('.', os.sep)

    packages_to_search = ['org.bouncycastle', 'net.java.otr4j.crypto', 'org.sqlite', 'android.support.v4',
                          'android.support.v7', 'android.support.v13']
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
            else:
                break
        else:
            # Searched for a package and found it!
            lib = database.session.query(database.Library).filter(
                database.Library.base_package == '.'.join(package)).first()
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


def recursive_iterate(parent):
    for f in os.listdir(parent.get_full_path()):
        if f.endswith('.smali'):
            in_sub_tree = True
            file = File(f, parent)
            parent.add_child_file(file)
        else:
            p = Package(f, parent)
            parent.add_child_package(p)
            recursive_iterate(p)


def new_iterate(path):
    class_paths = find_class_paths(path)
    base.dot_id_counter = 0
    root = Package('ROOT', parent=None, special=True)
    for folder in class_paths:
        special = Package(folder, root, True)
        special.set_special_path(os.path.join(path, folder))
        root.add_child_package(special)
        recursive_iterate(special)
    root.iterate_end_of_packages()
    return root


def compare(method, all_methods=None, hints=None):
    method.generate_ngrams()
    if hints is None:
        q_methods = all_methods
    else:
        if len(hints) == 0:
            print('HINTS 0')
        q_methods = apkdb.session.query(apkdb.MethodVersion).filter(apkdb.MethodVersion.file_id.in_(hints)).all()

    simhash = method.elsim_similarity_instructions()
    simhash_nodot = method.elsim_similarity_nodot_instructions()
    simhash_weak = method.elsim_similarity_weak_instructions()
    param_amount = len(method.get_params())
    new_hints = []
    for compare_method in q_methods:
        if param_amount != len((compare_method.to_apk_method()).get_params()):
            continue
        if compare_method.length < int(method.length - (float(method.length) / 10)) \
                or compare_method.length > int(method.length + float(method.length) / 10):
            continue
        sim_weak = simhash_weak.similarity(SimHash.from_string(compare_method.elsim_instr_weak_hash))
        if sim_weak > 0.75:
            sim_complete = simhash.similarity(SimHash.from_string(compare_method.elsim_instr_hash))
            sim_nodot = simhash_nodot.similarity(SimHash.from_string(compare_method.elsim_instr_nodot_hash))
            sim = max(sim_weak, sim_complete, sim_nodot)
            if sim > 0.90:
                ngram_set_m = set(method.ngrams)
                ngram_list_compare = list()
                for ngram in compare_method.threegrams:
                    ngram_list_compare.append((ngram.one, ngram.two, ngram.three))
                ngram_set_compare = set(ngram_list_compare)
                ngram_comparison = ngram_set_m.symmetric_difference(ngram_set_compare)
                if len(ngram_comparison) <= 0.2 * method.length:
                    if compare_method.method.file.id not in new_hints:
                        new_hints.append(compare_method.method.file.id)
    return new_hints


def deeplen(l):
    for e in l:
        if len(e) > 0:
            return True
    return False


def package_length(p):
    return len(p.split('.'))


def new_analyze(path):
    # android_manifest = ElementTree.parse(os.path.join(path, 'AndroidManifest.xml'))
    # root = android_manifest.getroot()
    # mains = search_mains(root)
    # print('>> Main activities found:', mains)

    root = new_iterate(path)

    # from graphviz import Digraph
    # dot = Digraph()
    # root.graph(dot, None, True)
    # dot.render('OUT.png', view=True)
    # with open('out.dot', 'w+') as f:
    #    f.write(dot.source)

    # node = root.child_packages[0]
    eops = root.find_eops()
    # files = []
    q_methods = apkdb.session.query(apkdb.MethodVersion).all()
    for eop in eops:
        if eop.is_obfuscated() < 0.825:
            if not base.deobfuscate_only:
                print(Fore.GREEN + 'Saving package to DB:', Fore.CYAN + eop.get_full_package() + Style.RESET_ALL)
                for file in eop.get_files():
                    file.generate_methods()
                    file.generate_sim_hashes()
                    file.generate_ngrams()
                eop.save_to_db()
            else:
                print('Skipping: ', eop.get_full_package(), ', it doesn\'t appear to be obfuscated')
            continue
        print(Fore.GREEN + 'Analyzing package:', Fore.CYAN + eop.get_full_package() + Style.RESET_ALL)
        eop_suggestions = list()
        for file in eop.get_files():
            file.generate_methods()
            for m in file.get_largest_function():
                m.generate_ngrams()
                if not m.is_significant() or 'constructor ' in m.signature or 'abstract ' in m.signature:
                    continue
                hints = compare(m, all_methods=q_methods, hints=None)
                if len(hints) == 0:
                    continue
                other_hints = []
                for other in file.get_largest_function():
                    if other == m:
                        continue
                    if not other.is_significant() or 'constructor ' in other.signature or 'abstract ' in other.signature:
                        continue
                    other_hints.append(compare(other, all_methods=q_methods, hints=hints))
                if deeplen(other_hints):
                    # print(Fore.CYAN + 'File', file.get_full_package(), 'may be:' + Style.RESET_ALL)
                    for hint in other_hints:
                        if len(hint) == 0:
                            continue
                        else:
                            for real_hint in hint:
                                f = apkdb.session.query(apkdb.File).filter(apkdb.File.id == real_hint).first()
                                # print(f)
                                lib = f.package.library
                                if (lib, f.package) not in eop_suggestions:
                                    eop_suggestions.append((lib, f.package))
                                    if eop_suggestions[-1] is None:
                                        print(f, lib, 'seems to be None?')
        if len(eop_suggestions) > 0:
            print(Fore.CYAN + 'EOP', eop.get_full_package(), 'may be:' + Style.RESET_ALL)
            for lib in eop_suggestions:
                other_package = '.'.join([lib[0].base_package, lib[1].name]) if len(lib[1].name) > 0 else lib[0].base_package
                if package_length(eop.get_full_package()) != package_length(other_package):
                    continue
                print(lib)
        else:
            print(Fore.CYAN + 'EOP', eop.get_full_package(), 'could', Fore.RED + 'not' + Fore.CYAN,
                  'be deobfuscated :(' + Style.RESET_ALL)

            '''
                    # SimHash comparison
                    simhash = m.elsim_similarity_instructions()
                    simhash_nodot = m.elsim_similarity_nodot_instructions()
                    possible_methods_simhash = dict()
                    possible_methods_ngram = dict()
                    param_amount = len(m.get_params())
                    for compare_method_v in q_methods:
                        if param_amount != len((compare_method_v.to_apk_method()).get_params()):
                            continue
                        if compare_method_v.length < int(m.length - (float(m.length) / 10)) \
                                or compare_method_v.length > int(m.length + float(m.length) / 10):
                            continue
                        sim = simhash.similarity(SimHash.from_string(compare_method_v.elsim_instr_hash))
                        sim2 = simhash_nodot.similarity(SimHash.from_string(compare_method_v.elsim_instr_nodot_hash))
                        sim = max(sim, sim2)
                        if sim >= 0.9999:
                            print('EXACT MATCH')
                            print(m.signature, '--', compare_method_v.method.signature)
                        if sim >= 0.9:

                            # Do NGRAM now!
                            ngram_set_m = set(m.ngrams)
                            ngram_list_compare = list()
                            for ngram in compare_method_v.threegrams:
                                ngram_list_compare.append((ngram.one, ngram.two, ngram.three))
                            ngram_set_compare = set(ngram_list_compare)
                            ngram_comparison = ngram_set_m.symmetric_difference(ngram_set_compare)
                            if compare_method_v.method.id not in possible_methods_ngram.keys():
                                possible_methods_ngram[compare_method_v.method.id] = {'m': compare_method_v.method,
                                                                                      'diff': len(ngram_comparison)}
                            else:
                                possible_methods_ngram[compare_method_v.method.id]['diff'] = min(
                                    possible_methods_ngram[compare_method_v.method.id]['diff'], len(ngram_comparison))
                            if compare_method_v.method.id not in possible_methods_simhash.keys():
                                possible_methods_simhash[compare_method_v.method.id] = compare_method_v.method

                    for method in possible_methods_simhash.values():
                        if method.file.id not in possible_files_simhash:
                            possible_files_simhash[method.file.id] = {'file': method.file, 'amount': 1}
                        else:
                            possible_files_simhash[method.file.id]['amount'] += 1
                    best_ngrams = sorted(possible_methods_ngram.values(), key=lambda x: x['diff'])[
                                  0:min(10, len(possible_methods_ngram))]
                    for result in best_ngrams:
                        if result['m'].file.id not in possible_files_ngram:
                            possible_files_ngram[result['m'].file.id] = {'file': result['m'].file, 'diffs': result['diff']}
                        else:
                            possible_files_ngram[result['m'].file.id]['diffs'] += result['diff']

            print(Fore.GREEN + 'File' + Fore.CYAN, file.get_full_package(),
                  Fore.GREEN + 'is most probably:' + Style.RESET_ALL)
            print('With Simhash:')
            pprint(sorted(possible_files_simhash.items(), key=lambda x: x[1]['amount'], reverse=True)[
                   0:min(5, len(possible_files_simhash))])
            print('With NGram:')
            pprint(sorted(possible_files_ngram.items(), key=lambda x: x[1]['diffs'])[
                   0:min(5, len(possible_files_ngram))])
            print()'''

            # for p in possible_files_simhash.values():
            #    if p['file'].package.library.base_package in p_dict_simhash:
            #        p_dict_simhash[p['file'].package.library.base_package] += p['amount']
            #    else:
            #        p_dict_simhash[p['file'].package.library.base_package] = p['amount']

            # print()
            # print(eop.get_full_package())
            # if p_dict_simhash:
            #    print(sorted(p_dict_simhash.items(), key=lambda x: x[1], reverse=True))
            # if p_dict_ngram:
            #    print(sorted(p_dict_ngram.items(), key=lambda x: x[1], reverse=True))

    """for f in files:
        for e in files:
            if e != f:
                filesim = 0
                for method in f.methods:
                    if not method.is_significant():
                        continue
                    fhash = method.elsim_similarity_instructions()
                    for m_2 in e.methods:
                        if not m_2.is_significant():
                            continue
                        ehash = m_2.elsim_similarity_instructions()
                        sim = fhash.similarity(ehash)
                        if sim > 0.9:
                            filesim += 1
                if len(f.methods) > 4 and float(filesim) / float(len(f.methods)) > 0.8:
                    print(f.name, '==', e.name)"""


def main():
    global threads
    parser = argparse.ArgumentParser(description='Deobfuscate Android Applications')
    parser.add_argument('apk', metavar='apk', type=str, help='The apk to unpack')
    parser.add_argument('-t', '--threads', dest='threads', action='store', nargs=1, type=int,
                        help='Maximum amount of threads used', default=4)
    parser.add_argument('-v', '--verbose', dest='verbose', action='store_true', help='Show more detailed information')
    parser.add_argument('-k', '--keep', dest='keep', action='store_true', help='Keep old folder')
    parser.add_argument('-sd', '--skip-decompile', dest='skip_decompile', action='store_true',
                        help='Skip decompilation')
    parser.add_argument('-sb', '--skip-build', dest='skip_build', action='store_true',
                        help='Skip recompilation / rebuilding apk')
    parser.add_argument('-s', '--skip', dest='skip_all', action='store_true', help='Skip all')
    parser.add_argument('-a', '--analyze', dest='analyze', action='store_true',
                        help='Analyze instead of deobfuscate. With this, you can add new stuff to the database.')
    parser.add_argument('-d', '--deobfuscate', dest='deobfuscate_only', action='store_true',
                        help='Only Deobfuscate, don\'t analyze!')
    args = parser.parse_args()

    colorama.init()

    apk_paths = os.path.abspath(args.apk)
    threads = args.threads
    if isinstance(threads, list):
        threads = threads[0]
    args.skip_decompile = True if args.skip_all else args.skip_decompile
    args.skip_build = True if args.skip_all else args.skip_build

    if os.path.isdir(apk_paths):
        apks = [os.path.join(apk_paths, x) for x in os.listdir(apk_paths) if x.endswith('.apk')]
    else:
        apks = [apk_paths]

    base.verbose = args.verbose
    base.deobfuscate_only = args.deobfuscate_only
    already_in_db = []
    for apk in apks:
        output_folder = os.path.join('decompiled', os.path.basename(apk)[:-4])

        print(Fore.GREEN + '> Starting deobfuscation process for:', apk)
        print('---------------------------------------------')
        print(Style.RESET_ALL)
        if not args.keep and os.path.exists(output_folder):
            print(Fore.RED + '>> Removing old output folder')
            print(Style.RESET_ALL)
            shutil.rmtree(output_folder)
        if not args.skip_decompile:
            run(['java', '-jar', 'apktool.jar', '-b', '-o', output_folder, 'd', apk])
            print(Fore.BLUE + '>> Decompiling to smali code done')
        print(Style.RESET_ALL)
        if not args.analyze:
            deobfuscate(os.path.join(os.getcwd(), output_folder))
            print(Fore.GREEN + '---------------------------------------------')
            print('Done deobfuscating...' + Style.RESET_ALL)
            if not args.skip_build:
                print('Rebuilding APK')
                run(['java', '-jar', 'apktool.jar', 'b', os.path.join(os.getcwd(), output_folder), '-o',
                     apk + '_new.apk'])
                if args.verbose:
                    base.verbose = True
                    print(Fore.LIGHTRED_EX + '---------------------------------------------')
                    print('Don\'t forget to sign your apk with the following commands:')
                    print(
                        'keytool -genkey -v -keystore my-release-key.keystore -alias alias_name -keyalg RSA -keysize 2048 -validity 10000')
                    print(
                        'jarsigner -verbose -sigalg SHA1withRSA -digestalg SHA1 -keystore my-release-key.keystore my_application.apk alias_name')
                    print('jarsigner -verify -verbose -certs my_application.apk')
                    print('zipalign -v 4 your_project_name-unaligned.apk your_project_name.apk')
        else:
            new_analyze(os.path.join(os.getcwd(), output_folder))
            # TODO: already_in_db.extend(analyze(os.path.join(os.getcwd(), output_folder)))

        if not args.keep and os.path.exists(output_folder):
            print(Fore.RED + '>> Removing output folder')
            print(Style.RESET_ALL)
            try:
                shutil.rmtree(output_folder)
            except OSError as e:
                print('Failed to remove folder', output_folder)
    if args.analyze:
        print(Fore.GREEN)
        pprint(already_in_db)
        print(Style.RESET_ALL)


if __name__ == '__main__':
    main()
