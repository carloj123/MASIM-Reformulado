import os
import signal
import shutil
import time
import subprocess
import pathlib
import socketio
import requests
import json
import sys
import psutil

root = str(pathlib.Path(__file__).resolve().parents[2])
temp_config = '/experiments/temp/temp-config.json'
default_config = '/experiments/temp/default-config.json'
reports_folder = '/experiments/temp/reports'
start_system_path = root + '/start_system.py'

base_url = '192.168.1.110'
api_port = 12345
connect_agent_url = f'http://{base_url}:{api_port}/connect_agent'
connect_monitor_url = f'http://{base_url}:{api_port}/connect_monitor'
sim_command = ['python3', start_system_path,
               *(f'-conf experiments/temp/temp-config.json -pyv 3 -g True -url {base_url} -secret temp -first_t 20').split(' ')]


agent_socket = socketio.Client()
monitor_socket = socketio.Client()
agent_token = None
monitor_token = None
agent_package_sizes = []
monitor_package_sizes = []

process_finished = False
experiments = [50, 100]
current_prob = None


@agent_socket.on('percepts')
def percepts(msg):
    global agent_package_sizes

    msg_size = sys.getsizeof(msg)
    agent_package_sizes.append(msg_size)

    agent_socket.emit('send_action', json.dumps({'token': agent_token, 'action': 'pass', 'parameters': []}))


@agent_socket.on('bye')
def finish(msg):
    global process_finished

    path = root + reports_folder + '/package_size_api_agent_' + str(current_prob) + '.csv'

    with open(path, 'w+') as report:
        for e in agent_package_sizes:
            report.write(str(e)+'\n')

    agent_socket.emit('disconnect_registered_agent', json.dumps({'token': agent_token}))
    agent_socket.disconnect()
    agent_package_sizes.clear()

    process_finished = True
    print('bye agent')


@monitor_socket.on('percepts')
def percepts(msg):
    global monitor_package_sizes

    msg_size = sys.getsizeof(msg)

    print(len(msg['environment']['events']), msg_size)

    monitor_package_sizes.append(msg_size)


@monitor_socket.on('bye')
def finish(msg):
    global monitor_package_sizes

    path = root + reports_folder + '/package_size_api_monitor_' + str(current_prob) + '.csv'

    with open(path, 'w+') as report:
        for e in monitor_package_sizes:
            report.write(str(e)+'\n')

    monitor_socket.disconnect()
    monitor_package_sizes.clear()


def set_environment_steps(prob):
    global current_prob
    current_prob = prob

    log(f'COMPLEXITY_{prob}', 'Setting the environment.')
    with open(root + default_config, 'r') as config:
        content = json.loads(config.read())

    content['generate']['flood']['probability'] = prob

    with open(root + temp_config, 'w') as config:
        config.write(json.dumps(content, sort_keys=False, indent=4))


def start_processes(experiment):
    global process_finished

    process_finished = False

    #null = open(os.devnull, 'w')
    log(f'COMPLEXITY_{experiment}', 'Start simulator process.')

    sim_proc = subprocess.Popen(sim_command)#, stdout=null, stderr=subprocess.STDOUT)

    log(f'COMPLEXITY_{experiment}', 'Waiting for the simulation start...')

    connect_monitor()
    connect_agent()

    while not process_finished:
        time.sleep(1)

    time.sleep(2)

    log(f'COMPLEXITY_{experiment}', 'Simulation finished, killing all processes.')

    current_process = psutil.Process(sim_proc.pid)
    children = current_process.children(recursive=True)
    for child in children:
        os.kill(child.pid, signal.SIGTERM)

    sim_proc.kill()

    del sim_proc


def connect_agent():
    global agent_socket
    global agent_token

    response = dict(result=False)
    while not response['result']:
        time.sleep(1)
        try:
            response = requests.post(connect_agent_url, json={'name': 'temp'}).json()
            agent_token = response['message']
        except Exception:
            continue

    agent_socket.connect(f'http://{base_url}:{api_port}')
    agent_socket.emit('register_agent', data=dict(token=agent_token))


def connect_monitor():
    global monitor_socket
    global monitor_token

    connected = False
    while not connected:
        try:
            monitor_socket.connect(f'http://{base_url}:{api_port}')
            connected = True
        except Exception:
            continue

    monitor_socket.emit('connect_monitor', data=dict())


def log(exp, message):
    print(f'[{exp}] ## {message}')


def start_experiments():
    for prob in experiments:
        log(f'COMPLEXITY_{prob}', 'Start new experiment.')

        set_environment_steps(prob)
        start_processes(prob)
        print('fim experimento')
        time.sleep(5)


if __name__ == '__main__':
    # Create temp file to run the experiments
    shutil.copy2(root + default_config, root + temp_config)
    # Start the first experiment
    start_experiments()

    print('[FINISHED] ## Finished all experiments')
    os.kill(os.getpid(), signal.SIGTERM)