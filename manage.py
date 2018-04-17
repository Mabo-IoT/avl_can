# -*- coding: utf-8 -*-

import argparse

import waitress

from Doctopus.web.app import get_app

try:
    from queue import Queue
except:
    from Queue import Queue

from logging import getLogger
from threading import Thread

from Doctopus.lib.Sender import Sender
from Doctopus.lib.watchdog import WatchDog
from Doctopus.lib.communication import Communication
from Doctopus.lib.logging_init import setup_logging
from Doctopus.lib.transport import Transport
from Doctopus.utils.util import get_conf

log = getLogger("Doctopus.start")


def start_ziyan():
    from plugins.your_plugin import MyCheck, MyHandler

    # init queues
    queue = {'data_queue': Queue(), 'sender': Queue()}

    # load all configs
    all_conf = get_conf('conf/conf.toml')

    # init log config
    setup_logging(all_conf['log_configuration'])

    # init instances
    checker = MyCheck(all_conf)
    handler = MyHandler(all_conf)
    sender = Sender(all_conf)
    communication = Communication(all_conf)

    # name instances
    checker.name = 'checker'
    handler.name = 'handler'
    sender.name = 'sender'

    # init work threads set
    workers = [checker, handler]

    thread_set = dict()

    # start workers instance
    for worker in workers:
        thread = Thread(target=worker.work, args=(queue,), name='%s' % worker.name)
        thread.setDaemon(True)
        thread.start()
        thread_set[worker.name] = thread

    # init send set
    send_set = [communication, sender]
    for send in send_set:
        thread = Thread(target=send.work, args=(queue,), name='%s' % send.name)
        thread.setDaemon(True)
        thread.start()

    # start watch instance
    watch = WatchDog(all_conf)
    watch = Thread(target=watch.work, name='%s' % watch.name, args=(thread_set, queue, workers))
    watch.setDaemon(True)
    watch.start()


def start_chitu():
    # load all configs
    all_conf = get_conf('conf/conf.toml')

    # init log config
    setup_logging(all_conf['log_configuration'])

    thread_set = dict()
    queue = None
    workers = list()

    for redis_address in all_conf['redis']['address']:
        work = Transport(all_conf, redis_address)
        work.name = 'redis_' + str(redis_address['db'])
        thread = Thread(target=work.work, args=(), name='%s' % work.name)
        thread.setDaemon(True)
        thread.start()
        workers.append(work)
        thread_set[work.name] = thread

    # start communication instance
    communication = Communication(all_conf)
    thread = Thread(target=communication.work, args=(), name='%s' % communication.name)
    thread.setDaemon(True)
    thread.start()

    # start watch instance
    watch = WatchDog(all_conf)
    watch = Thread(target=watch.work, name='watchdog', args=(thread_set, queue, workers))
    watch.setDaemon(True)
    watch.start()


if __name__ == '__main__':
    parse = argparse.ArgumentParser(prog='Doctopus', description='A distributed data collector.',
                                    usage="\n"
                                          "python manage.py [-h] [-a ACTION] [-v] [-t {ziyan,chitu}] [-i IP] [-p PORT]")
    parse.add_argument('-a', '--action', action='store', default='run', help='Run/test the project, default run')
    parse.add_argument('-v', '--version', action='version', default=None, version='%(prog)s 0.2.0')
    parse.add_argument('-t', '--target', default='ziyan', choices=['ziyan', 'chitu'],
                       help='selelct the target, default ziyan')
    parse.add_argument('-i', '--ip', default='0.0.0.0',
                       help="Hostname or IP address on which to listen, default is '0.0.0.0', "
                            "which means 'all IP addresses on this host'.")
    parse.add_argument('-p', '--port', default='8000', help="TCP port on which to listen, default is '8000'.")

    command = parse.parse_args().action
    target = parse.parse_args().target
    host = parse.parse_args().ip
    port = parse.parse_args().port
    version = parse.parse_args().version

    if version:
        print(version)

    elif command == 'run':

        if target == 'ziyan':
            start_ziyan()

        if target == 'chitu':
            start_chitu()
            port = port if port != '8000' else str(int(port) + 1)

        log.info("Serving on http://%s:%s", host, port)
        waitress.serve(get_app(), host=host, port=port, _quiet=True)

    elif command == 'test':
        pass
