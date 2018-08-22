import os, psutil, re, shutil
from subprocess import Popen, check_output, DEVNULL
import argparse
import yaml
import resource
import time
import math
import logging
from datetime import timedelta, datetime


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('-l', dest="ls_base", required=True, help="specify the installation directory of LigandScout")
    parser.add_argument('-y', dest="yaml", required=True, help="specify optinos for test of LigandScout")
    args = parser.parse_args()
    return args

def load_yaml(args):
    with open(args.yaml, 'r') as stream:
        try:
            settingsMap = yaml.load(stream)
        except yaml.YAMLError as exc:
            print(exc)    
    return settingsMap


def _monitoring_memory_consumption():
    all_pids_as_list = _get_pid_list()
    memory = 0
    for pid in all_pids_as_list:
        try:
            process = psutil.Process(pid.pid)
            memory += process.memory_info().rss
        except psutil.NoSuchProcess:
            return 0
    logging.info('Memory consumption: %s' % str(_convert_size(memory)))
    return _convert_size(memory)

def _monitoring_cpu_consumption():
    all_pids_as_list = _get_pid_list()
    cpu = 0
    for pid in all_pids_as_list:
        try:
            process = psutil.Process(pid.pid)
            cpu += process.cpu_percent(interval=1)

        except psutil.NoSuchProcess:
            return 0
    logging.info('CPU-Usage on %d threats : %f' % ( int(len(all_pids_as_list)), float(round(cpu, 1))))
    return round(cpu, 1)

def _get_pid_list():
    "Return a list of processes matching 'name'."
    ls = []
    for p in psutil.process_iter(attrs=['name']):
        if p.info['name'] == 'java':
            ls.append(p)

    return ls

def print_log(str_arg):
    logging.info(str_arg)
    print(str_arg)

def monitor_process(proc):
    pid = proc.pid
    logging.info('Process-ID: %d' % pid)
    time.sleep(5)
    all_pids_as_list = _get_pid_list()
    logging.info('- Watching %d active threats' % len(all_pids_as_list))

    for pid in all_pids_as_list:
        logging.info('  + Watching: %s' % str(pid))

    memory = []
    cpu = []
    nr_of_steps = 0

    while(proc.poll() == None):
        memory_at_the_moment, units = _monitoring_memory_consumption().split()
        if memory_at_the_moment != 0:
            memory.append(float(memory_at_the_moment))
        cpu_at_the_moment = _monitoring_cpu_consumption()
        if cpu_at_the_moment != 0:
            cpu.append(float(cpu_at_the_moment))
        nr_of_steps += 1
        time.sleep(5)

    print_log('Average CPU usage: %f' % round(sum(cpu)/ nr_of_steps, 1))
    print_log('Highest CPU usage: %f' % round(max(cpu)))
    print_log('Average memory usage: [%s] %f' % (str(units), round(sum(memory)/ nr_of_steps, 1)))
    print_log('Highest memory usage: [%s] %f' % (str(units), round(max(memory))))
    
    d = dict()
    d['average-cpu'] = round(sum(cpu)/ nr_of_steps, 1)
    d['highest-cpu'] = round(round(max(cpu)))
    d['average-mem'] = round(sum(memory)/ nr_of_steps, 1)
    d['highest-mem'] = round(max(memory))
    return d


def _convert_size(size_bytes):
   if size_bytes == 0:
       return "0B"
   size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
   i = int(math.floor(math.log(size_bytes, 1024)))
   p = math.pow(1024, i)
   s = round(size_bytes / p, 2)
   return "%s %s" % (s, size_name[i])

def _get_time(took_time):
    sec = timedelta(seconds=int(took_time))
    d = datetime(1,1,1) + sec
    print("DAYS:HOURS:MIN:SEC")
    print_log("%d:%d:%d:%d" % (d.day-1, d.hour, d.minute, d.second))
    return "%d:%d:%d:%d" % (d.day-1, d.hour, d.minute, d.second)

def _write_test_result(cmd_line_tool, test_nr, value, type_of_test):

    file = open('../test_results/' + str(cmd_line_tool) + '_' + str(test_nr) + '_' + str(type_of_test) + '.txt', 'a')
    file.write(str(value) + ' ,')


def evaluating_output(cmd_line_tool, took_time, tests, output, test_nr, d, logfile):

    for key in d:
        _write_test_result(cmd_line_tool, test_nr, d[key], key)
 
    if 'time' in tests:
        #value = _get_time(took_time)
        value = int(took_time)
        _write_test_result(cmd_line_tool, test_nr, value, 'time')

    if 'inserted' in tests:
        inserted = None
        try:
            with open(logfile, 'r') as f:
                for line in f:
                    if 'Molecules inserted' in line:
                        inserted = int(re.search(r'\d+', line).group())
                
        except IOError:
            print_log('Could not read file: %s' % logfile)
        print_log('Nr of molecules that idbgen inserted: %i ' % inserted)
        _write_test_result(cmd_line_tool, test_nr, inserted, 'inserted')

    if 'duplicate' in tests:
        output_base = output.split('.')[0]
        nr_of_found_duplicates = 0
        found_duplicates = []

        log_file = '../test_data/' + str(output_base) + '-failed.log'
        try:
            with open(log_file, 'r') as f:
                for line in f:
                    if 'duplicate' in line:
                        nr_of_found_duplicates += 1
                        found_duplicates.append(line)
                
        except IOError:
            print_log('Could not read file: %s' % log_file)
        print_log('Nr of molecules that were duplicates: %i ' % nr_of_found_duplicates)
        _write_test_result(cmd_line_tool, test_nr, nr_of_found_duplicates, 'duplicate')

    if 'failed' in tests:
        output_base = output.split('.')[0]
        nr_of_failed_molecules = 0
        failed_molecules = []

        log_file = '../test_data/' + str(output_base) + '-failed.log'
        try:
            with open(log_file, 'r') as f:
                for line in f:
                    if 'failed' in line:
                        nr_of_failed_molecules += 1
                        failed_molecules.append(line)
                
        except IOError:
            print_log('Could not read file: %s' % log_file)
        print_log('Nr of molecules for which idbgen failed: %i ' % nr_of_failed_molecules)
        _write_test_result(cmd_line_tool, test_nr, nr_of_failed_molecules, 'failed')

    if 'hits' in tests:
        found_hits = None
        try:
            with open(logfile, 'r') as f:
                for line in f:
                    if 'virtual hits' in line:
                        found_hits = int(re.search(r' \d+ ', line).group())
                
        except IOError:
            print_log('Could not read file: %s' % logfile)
        print_log('Nr of molecules that iscreen found: %i ' % found_hits)
        _write_test_result(cmd_line_tool, test_nr, found_hits, 'hits')


def testing_idbgen(args, settingsMap, date):
    print_log('################################')
    print_log('################################')
    print_log('idbgen test started')
    print_log('################################')
    print_log('################################')

    
    for test in settingsMap['idbgen']:
        print_log('################################')
        print_log('Starting with : %s' % test)
        print_log('################################')

        input = '../data/' + settingsMap['idbgen'][test]['input']
        output = '../test_data/' + settingsMap['idbgen'][test]['output']
        arguments = settingsMap['idbgen'][test]['options']
        tests = settingsMap['idbgen'][test]['evaluate']
        executable = args.ls_base + '/idbgen' 

        print_log('Calling %s' % executable)
        print_log('Input: %s' % input)
        logfile = '../test_data/' + output.split('/')[-1].split('.')[0] + '.log'

        print_log('Output: %s' % output)
        print_log('Options: %s' % arguments)
        print_log('Testing: %s' % tests)
        print_log('Logfile: %s' % logfile)

        ti0 = time.time()
        proc = Popen([executable, '--input', input, '--output', output, '--log', logfile, arguments])#, stdout=DEVNULL, stderr=DEVNULL)
        d = monitor_process(proc)
        ti1 = time.time()
        took_time = ti1 - ti0 - 5 # time in seconds (-5 because of the sleep call in monitor_process())
        time.sleep(5)

        evaluating_output('idbgen', took_time, tests, str(settingsMap['idbgen'][test]['output']), test, d, logfile)
        
        _write_test_result('idbgen', test, date, 'dates')

def testing_iscreen(args, settingsMap, date):
    print_log('################################')
    print_log('################################')
    print_log('iscreen test started')
    print_log('################################')
    print_log('################################')

    
    for test in settingsMap['iscreen']:
        print_log('################################')
        print_log('Starting with : %s' % test)
        print_log('################################')


        screening_library = '../test_data/' + settingsMap['iscreen'][test]['library']
        ph = '../data/' + settingsMap['iscreen'][test]['ph']
        arguments = settingsMap['iscreen'][test]['options']
        hitlist = '../test_data/' + settingsMap['iscreen'][test]['hitlist']
        logfile = '../test_data/' + hitlist.split('/')[-1].split('.')[0] + '.log'
        tests = settingsMap['iscreen'][test]['evaluate']
        executable = args.ls_base + '/iscreen' 

        print_log('Calling %s' % executable)
        print_log('Screening library: %s' % screening_library)
        print_log('Pharmacophore model: %s' % ph)
        print_log('Hitlist: %s' % hitlist)
        print_log('Options: %s' % arguments)
        print_log('Testing: %s' % tests)
        print_log('Logfile: %s' % logfile)


        ti0 = time.time()
        proc = Popen([executable, '--database', screening_library, '--query', ph, '--output', hitlist, '--log',  logfile, arguments])#, stdout=DEVNULL, stderr=DEVNULL)
        d = monitor_process(proc)
        ti1 = time.time()
        took_time = ti1 - ti0 - 5 # time in seconds (-5 because of the sleep call in monitor_process())
        time.sleep(5)

        evaluating_output('iscreen', took_time, tests, str(settingsMap['idbgen'][test]['output']), test, d, logfile)

        _write_test_result('iscreen', test, date, 'dates')


def process_yaml(args, settingsMap):
    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print_log(date)

    # start with idbgen
    testing_idbgen(args, settingsMap, date)
    # testing iscreen
    testing_iscreen(args, settingsMap, date)


if __name__ == '__main__':
    
    logging.basicConfig(filename='../log/LS_executable_test.log',level=logging.DEBUG)
    logging.basicConfig(format='%(asctime)s %(message)s')
    logging.info('Started')

    output_dir = '../test_data'

    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir)


    args = parse_arguments()
    settingsMap = load_yaml(args)
    process_yaml(args, settingsMap)

    logging.info('Finished')

