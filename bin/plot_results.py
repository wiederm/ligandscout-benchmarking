import os
import matplotlib.pyplot as plt
from collections import defaultdict
import csv

def _create_table():

    directory = os.fsencode('../test_results/')
    d = defaultdict(lambda: defaultdict(defaultdict))

    for file in os.listdir(directory):
        filename = os.fsdecode(file)
        if filename.endswith(".txt"):
            executabe, test_nr, kind_of_test = filename.split('_')
            kind_of_test= str(kind_of_test).replace('.txt', '')
            #print(executabe, test_nr, kind_of_test)
            file_path = os.path.join(directory, file)
            with open(file_path, 'r') as csvfile:
                reader = csv.reader(csvfile, delimiter=',')
                for row in reader:
                    #print(row)
                    pass

            d[executabe][test_nr][kind_of_test] = row
        else:
            continue

    return d

def _plot(table):

    for executable in table:
        for test in table[executable]:
            print('##################')
            print('##################')
            print(test)
            i = 1
            title = executable + ' ' + test
            plot_name = executable + '_' + test
            plt.suptitle(title , fontsize=10)
            color = ['red', 'black', 'blue', 'brown', 'green', 'yellow', 'pink', 'blueviolet', 'crimson']
            for idx, kind_of_test in enumerate(table[executable][test]):
                print(kind_of_test)

                if kind_of_test == 'dates':
                    continue
                plt.subplot(len(table[executable][test]), 1, i)
                plt.ylabel(kind_of_test, fontsize=4)
                plt.xlabel('dates', fontsize=4)

                plt.plot(table[executable][test]['dates'][:-1], table[executable][test][kind_of_test][:-1], 'o', label=kind_of_test, color=color[idx])
                i += 1
                plt.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)

            plt.subplots_adjust()  
            plt.xticks(rotation=45)
            plt.savefig(plot_name + '.svg')
            plt.close()


if __name__ == '__main__':
    table = _create_table()
    _plot(table)

