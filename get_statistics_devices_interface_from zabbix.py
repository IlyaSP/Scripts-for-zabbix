# -*- coding: utf-8 -*-

from pyzabbix import ZabbixAPI
import re
import operator
import datetime
import threading
import queue
import time
import sys


def get_statistics(work_queue):
    """
    Function for obtaining statistics on loading interfaces from ZABBIX for groups of devices falling under the
    conditions search.
    Функция для получения статистики по загрузки интерфесов из заббикса для групп устройств попадающих под условия
    поиска.
    """

    while True:
        # Если заданий нет - закончим цикл
        # If there are no jobs, finish cycle
        if work_queue.empty():
            sys.exit()
        # Получаем задание из очереди
        # get the job from the queue
        i = work_queue.get()
        # print('Queue: %s started' % i)

        host_name = i['name']
        host_id = int(i['hostid'])

        """
        receiving items for the host. The search key contains word 'Alias' and puts in the variable 'items'
        name parameter and last value parameter
        получаем список значения для хоста. Ключевое слово для поиска значений содержит слово 'Alias', помещаем в 
        переменную 'items' имя параметра и последнее значение параметра.
        """

        items = z.item.get(hostids=host_id, output=['name', 'lastvalue', 'key_'], search={'key_': 'Alias'})

        for item in items:
            """ 
            check that the variable matches the pattern. If it matches then to the variable "key" we place the 
            result of the search. if not match the value 'None' 
            проверяем, что значение переменной совпадает с регулярным выражением. Если совпадение есть, помещаем 
            результат поиска в переменную "key", если совпадения нет помещаем значение 'None'.
            """
            if re.search(
                    r'.*telecom.*|.*nternet.*|.*TTK*|.*nteroute.*|.*MPLS.*|.*nterroute.*|.*ee[lL]ine.*|.*ISP.*',
                    item['lastvalue']) is not None:
                key = re.search(r'\[.*\]', item['key_']).group(0)
                break
            else:
                key = 'None'

        if key != 'None':
            """
            If the value variable 'key' not equal to 'None', get value of incoming and outgoing traffic on 
            the interface and put in the corresponding dictionary
            Если значение переменной 'key' не равно 'None', получаем значения входящего и исходящего трафика на 
            интерфейсах и помещаем в соответствующие словари
            """
            key_traffic_in = 'ifInOctets' + key
            key_traffic_out = 'ifOutOctets' + key
            item_traffic_in = z.item.get(hostids=host_id, output=['name', 'lastvalue', 'key_'],
                                         search={'key_': key_traffic_in})
            item_traffic_out = z.item.get(hostids=host_id, output=['name', 'lastvalue', 'key_'],
                                          search={'key_': key_traffic_out})

            if len(item_traffic_in) == 0 | len(item_traffic_out) == 0:
                trafic_in = 0
                trafic_out = 0
                dict_traffic_in[host_name] = trafic_in
                dict_traffic_out[host_name] = trafic_out
            else:
                trafic_in = item_traffic_in[0]['lastvalue']
                trafic_out = item_traffic_out[0]['lastvalue']
                dict_traffic_in[host_name] = float(trafic_in)
                dict_traffic_out[host_name] = float(trafic_out)

        else:
            trafic_in = 0
            trafic_out = 0
            dict_traffic_in[host_name] = trafic_in
            dict_traffic_out[host_name] = trafic_out

        work_queue.task_done()
        print('Queue: %s done' % i)
        # print(u'Очередь: %s завершилась' % i)


try:
    start = datetime.datetime.now()
    z = ZabbixAPI('http://10.116.2.100', user='permogorsky_is@moscow', password='')  # connect to zabbix server
    answer = z.do_request('apiinfo.version')
    print("Version:", answer['result'])

    groups_id = []
    groups = z.hostgroup.get(output=['itemid', 'name'])  # get all host groups on the server

    for group in groups:
        """ 
        If name group matches the pattern, put the group number in the list 'group_id' 
        Если имя группы сщвпадает с регулярным выражением, помещаем номер группы в список 'group_id' 
        """
        if re.search(r'.*ranch.*', group["name"]):
            groups_id.append(group['groupid'])
            print(group['groupid'], group['name'])
            continue

    print('list groups =', groups_id)

    if len(groups_id) == 0:
        raise SystemExit(111)
    else:
        hosts = []
        for groupids in groups_id:
            """
            Search of obtained groups and getting list of hosts in the group
            Перебор полученных групп и получение списка хостов входящих в эти группы. Заполнение этими хостами массива
            в котором хранятся хосты из всех групп
            """
            hosts_in_group = z.host.get(groupids=groupids, output=['hostid', 'name'])

            for host in hosts_in_group:
                hosts.append(host)
    # print(hosts)

    dict_traffic_in = {}  # dictionary for storing a pair of values. name - incoming traffic on interface
    dict_traffic_out = {}  # dictionary for storing a pair of values. name - outgoing traffic on interface

    # Создаем FIFO очередь
    # Create a FIFO queue
    work_queue = queue.Queue()

    # Заполняем очередь заданиями
    # Fill the queue with tasks
    for host in hosts:
        work_queue.put(host)

    print('queue length = ', len(work_queue.queue))

    for i in range(17):
        # print(u'Flow', str(i), u'start')
        # print(u'Поток', str(i), u'стартовал')
        print("Number of active flows: ", threading.activeCount())
        # print(u"Количчество активных потоков: ", threading.activeCount())
        t1 = threading.Thread(target=get_statistics, args=(work_queue,))
        t1.setDaemon(True)
        t1.start()
        time.sleep(0.0001)

    # Ставим блокировку до тех пор пока не будут выполнены все задания
    # Set the lock until all tasks are completed
    work_queue.join()

    """ 
    Sorting a dictinory with incoming traffic on the interface in descending order
    Сортируем словарь с входящим трафиком на интерфейсе по убыванию
    """
    sorted_traffic_in = sorted(dict_traffic_in.items(), key=operator.itemgetter(1), reverse=True)
    for i in sorted_traffic_in:
        print(i[0] + ': ', str(round(dict_traffic_in.get(i[0]) / 1048576, 2)) + ' Mbit/s/',
              str(round(dict_traffic_out.get(i[0]) / 1048576, 2)) + ' Mbit/s')

    end = datetime.datetime.now()
    print("lead time: ", end - start)

except Exception as e:
    print(e)
