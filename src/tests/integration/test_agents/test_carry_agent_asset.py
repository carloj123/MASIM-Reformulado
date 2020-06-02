import time
import json
import requests
import socketio


agent = {'name': 'carrying_agent'}
carried_asset = {'name': 'carried_asset'}

waits = []
responses = []


carrying_socket = socketio.Client()
carried_socket = socketio.Client()
token = None
carried_token = None


def connect_actors():
    global token, carried_token

    response = requests.post('http://127.0.0.1:12345/connect_agent', json=json.dumps(agent)).json()
    token = response['message']
    requests.post('http://127.0.0.1:12345/register_agent', json=json.dumps({'token': token}))
    carrying_socket.emit('connect_registered_agent', data=json.dumps({'token': token}))

    carried_response = requests.post('http://127.0.0.1:12345/connect_asset', json=json.dumps(carried_asset)).json()
    carried_token = carried_response['message']
    requests.post('http://127.0.0.1:12345/register_asset', json=json.dumps({'token': carried_token}))
    carried_socket.emit('connect_registered_asset', data=json.dumps({'token': carried_token}))


@carrying_socket.on('action_results')
def carry_action_results(msg):
    msg = json.loads(msg)

    if msg['environment']['step'] == 1:
        carrying_socket.emit('send_action', json.dumps({'token': token, 'action': 'carry', 'parameters': [carried_token]}))

    else:
        responses.append(msg['agent']['last_action_result'])
        carrying_socket.emit('disconnect_registered_agent', data=json.dumps({'token': token}), callback=quit_program)


@carried_socket.on('action_results')
def carried_action_results(msg):
    msg = json.loads(msg)

    if msg['environment']['step'] == 1:
        carried_socket.emit('send_action', json.dumps({'token': carried_token, 'action': 'getCarried', 'parameters': [token]}))

    else:
        responses.append(msg['social_asset']['last_action_result'])
        carried_socket.emit('disconnect_registered_asset', data=json.dumps({'token': token}), callback=quit_program)


def quit_program(*args):
    waits.append(True)


def test_cycle():
    carrying_socket.connect('http://127.0.0.1:12345')
    carried_socket.connect('http://127.0.0.1:12345')
    connect_actors()
    while len(waits) < 2:
        time.sleep(0.2)

    carrying_socket.disconnect()
    carried_socket.disconnect()

    assert all(responses)


if __name__ == '__main__':
    try:
        test_cycle()
        print(True)
    except AssertionError:
        print(False)
