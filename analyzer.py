__author__ = 'ohaz'
from pprint import pprint

# ATTENTION: This is an old, unused file!


class Analyzer:

    def analyze(self, api_counter, function_comparator):
        print('>>>>> ANALYZING')
        pprint(api_counter)
        pprint(function_comparator)
        exit()
        for api_element in api_counter:
            for function_comparator_key, function_comparator_value in function_comparator.items():
                if function_comparator_value['error'] > 20:
                    continue
                print(api_element[0], api_element[1])
                print(function_comparator_key, function_comparator_value)
                if function_comparator_key.startswith(api_element[1]['lib']['package']):
                    print('-------------------------')
                    print('Found match', function_comparator_key, ':\n',
                          api_element, 'with', '\n',
                          function_comparator_value
                          )

        #pprint(api_counter)