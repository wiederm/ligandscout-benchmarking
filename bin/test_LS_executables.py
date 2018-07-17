import os, psutil
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
            print('No such process ...')
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
            print('No such process ...')
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
    time.sleep(10)
    all_pids_as_list = _get_pid_list()
    logging.info('- Watching %d active threats' % len(all_pids_as_list))

    for pid in all_pids_as_list:
        logging.info('  + Watching: %s' % str(pid))

    memory = []
    cpu = []
    nr_of_steps = 0

    while(proc.poll() == None):
        memory.append(float(_monitoring_memory_consumption().split()[0]))
        cpu.append(float(_monitoring_cpu_consumption()))
        nr_of_steps += 1
        time.sleep(10)

    print_log('Average CPU usage: %f' % round(sum(cpu)/ nr_of_steps, 1))
    print_log('Highest CPU usage: %f' % round(max(cpu)))
    print_log('Average memory usage: %f' % round(sum(memory)/ nr_of_steps, 1))
    print_log('Highest memory usage: %f' % round(max(memory)))


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

def _write_test_result(test_nr, value, type_of_test):

    file = open(str(test_nr) + '_' + str(type_of_test) + '.txt', 'w+')
    file.write(value)


def _test_for_duplicates_in_log():
    pass

def evaluating_output(took_time, tests, output, test_nr):
    
    if 'time' in tests:
        value = _get_time(took_time)
        _write_test_result(test_nr, value, 'time')


    if 'duplicate' in tests:
        
        output_base = output.split('.')[0]
        nr_of_found_duplicates = 0
        found_duplicates = []

        log_file = '../data/' + str(output_base) + '-failed.log'
        try:
            with open(log_file, 'r') as f:
                line = f.readline()
                if 'duplicate' in line:
                    nr_of_found_duplicates += 1
                    found_duplicates.append(line)
                
        except IOError:
            print_log('Could not read file: %s' % log_file)
        print_log('Nr of molecules that were duplicates: %i ' % nr_of_found_duplicates)
        print(found_duplicates)
        _write_test_result(test_nr, nr_of_found_duplicates, 'duplicate')


    if 'failed' in tests:
        
        output_base = output.split('.')[0]
        nr_of_failed_molecules = 0
        failed_molecules = []

        log_file = '../data/' + str(output_base) + '-failed.log'
        try:
            with open(log_file, 'r') as f:
                line = f.readline()
                if 'failed' in line:
                    nr_of_failed_molecules += 1
                    failed_molecules.append(line)
                
        except IOError:
            print_log('Could not read file: %s' % log_file)
        print_log('Nr of molecules for which idbgen failed: %i ' % nr_of_failed_molecules)
        print(failed_molecules)
        _write_test_result(test_nr, nr_of_failed_molecules, 'failed')


    if 'hits' in tests:
        pass


def testing_idbgen(args, settingsMap):
    print_log('################################')
    print_log('################################')
    print_log('idbgen test started')
    print_log('################################')
    print_log('################################')

    
    for test in settingsMap['idbgen']:
        print_log('Starting with : %s' % test)

        input = '../data/' + settingsMap['idbgen'][test]['input']
        output = '../data/' + settingsMap['idbgen'][test]['output']
        arguments = settingsMap['idbgen'][test]['options']
        tests = settingsMap['idbgen'][test]['evaluate']
        executable = args.ls_base + '/idbgen' 

        print_log('Calling %s' % executable)
        print_log('Input: %s' % input)
        print_log('Output: %s' % output)
        print_log('Options: %s' % arguments)
        print_log('Testing: %s' % tests)

        ti0 = time.time()
        proc = Popen([executable, '--input', input, '--output', output, arguments])#, stdout=DEVNULL, stderr=DEVNULL)
        monitor_process(proc)
        time.sleep(5)
        ti1 = time.time()
        took_time = ti1 - ti0 # time in seconds

        evaluating_output(took_time, tests, str(settingsMap['idbgen'][test]['output']), test)

def testing_iscreen(args, settingsMap):
    print_log('################################')
    print_log('################################')
    print_log('iscreen test started')
    print_log('################################')
    print_log('################################')

    
    for test in settingsMap['iscreen']:
        print_log('Starting with : %s' % test)

        screening_library = '../data/' + settingsMap['iscreen'][test]['library']
        ph = '../data/' + settingsMap['iscreen'][test]['ph']
        arguments = settingsMap['iscreen'][test]['options']
        hitlist = settingsMap['iscreen'][test]['hitlist']
        tests = settingsMap['iscreen'][test]['evaluate']
        executable = args.ls_base + '/iscreen' 

        print_log('Calling %s' % executable)
        print_log('Screening library: %s' % screening_library)
        print_log('Pharmacophore model: %s' % ph)
        print_log('Hitlist: %s' % hitlist)
        print_log('Options: %s' % arguments)
        print_log('Testing: %s' % tests)

        ti0 = time.time()
        proc = Popen([executable, '--database', screening_library, '--query', ph, '--output', hitlist, arguments])#, stdout=DEVNULL, stderr=DEVNULL)
        monitor_process(proc)
        time.sleep(5)
        ti1 = time.time()
        took_time = ti1 - ti0 # time in seconds

        evaluating_output(took_time, tests, str(settingsMap['idbgen'][test]['output']), test)


def process_yaml(args, settingsMap):

    # start with idbgen
    testing_idbgen(args, settingsMap)
    testing_iscreen(args, settingsMap)


if __name__ == '__main__':
    
    logging.basicConfig(filename='../log/LS_executable_test.log',level=logging.DEBUG)
    logging.basicConfig(format='%(asctime)s %(message)s')
    logging.info('Started')

    args = parse_arguments()
    settingsMap = load_yaml(args)
    process_yaml(args, settingsMap)

    logging.info('Finished')

