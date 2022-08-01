import json
from queue import Queue
from random import randint
import time
from os.path import exists
import os


q = Queue()
completed_tasks = set()
results = dict()
exceptions = dict()


def get_json(file_path):
    request_id = randint(1, 1000000000000)
    q.put({'action': 'read', 'file_path': file_path, 'request_id': request_id})
    while True:
        time.sleep(0.01)
        if request_id in completed_tasks:
            if request_id in exceptions.keys():
                e = exceptions.pop(request_id)
                raise e
            completed_tasks.discard(request_id)
            reply = results.pop(request_id)
            return reply


def put_json(file_path, data):
    request_id = randint(1, 1000000000000)
    q.put({'action': 'write', 'file_path': file_path, 'data': data, 'request_id': request_id})
    while True:
        time.sleep(0.01)
        if request_id in completed_tasks:
            if request_id in exceptions.keys():
                e = exceptions.pop(request_id)
                raise e
            completed_tasks.discard(request_id)
            return True


def post_new_block(file_path, data):
    request_id = randint(1, 1000000000000)
    q.put({'action': 'post_new_block', 'file_path': file_path, 'data': data, 'request_id': request_id})
    while True:
        time.sleep(0.01)
        if request_id in completed_tasks:
            if request_id in exceptions.keys():
                e = exceptions.pop(request_id)
                raise e
            completed_tasks.discard(request_id)
            reply = results.pop(request_id)
            return reply


def remove_file(file_path):
    request_id = randint(1, 1000000000000)
    q.put({'action': 'remove_file', 'file_path': file_path, 'request_id': request_id})
    while True:
        time.sleep(0.01)
        if request_id in completed_tasks:
            if request_id in exceptions.keys():
                e = exceptions.pop(request_id)
                raise e
            completed_tasks.discard(request_id)
            return True


def rename_file(file_path_old, file_path_new):
    request_id = randint(1, 1000000000000)
    q.put({'action': 'rename_file', 'file_path_old': file_path_old, 'file_path_new': file_path_new, 'request_id': request_id})
    while True:
        time.sleep(0.01)
        if request_id in completed_tasks:
            if request_id in exceptions.keys():
                e = exceptions.pop(request_id)
                raise e
            completed_tasks.discard(request_id)
            return True


def task_processor():
    while True:
        if q.empty():
            time.sleep(0.01)
            continue
        task = q.get()
        if task['action'] == 'read':
            try:
                with open(task['file_path'], 'r') as f:
                    data = json.loads(f.read())
                results[task['request_id']] = data
            except Exception as e:
                exceptions[task['request_id']] = e
            finally:
                completed_tasks.add(task['request_id'])
        elif task['action'] == 'write':
            try:
                with open(task['file_path'], 'w') as f:
                    json.dump(task['data'], f)
            except Exception as e:
                exceptions[task['request_id']] = e
            finally:
                completed_tasks.add(task['request_id'])
        elif task['action'] == 'post_new_block':
            if exists(task['file_path']):
                results[task['request_id']] = 'Fail'
                completed_tasks.add(task['request_id'])
            else:
                try:
                    with open(task['file_path'], 'w') as f:
                        json.dump(task['data'], f)
                    results[task['request_id']] = 'Success'
                except Exception as e:
                    exceptions[task['request_id']] = e
                finally:
                    completed_tasks.add(task['request_id'])
        elif task['action'] == 'remove_file':
            try:
                os.remove(task['file_path'])
            except Exception as e:
                exceptions[task['request_id']] = e
            finally:
                completed_tasks.add(task['request_id'])
        elif task['action'] == 'rename_file':
            try:
                os.rename(task['file_path_old'], task['file_path_new'])
            except Exception as e:
                exceptions[task['request_id']] = e
            finally:
                completed_tasks.add(task['request_id'])
