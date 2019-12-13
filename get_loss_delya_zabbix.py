# -*- coding: utf-8 -*-
from pyzabbix.api import ZabbixAPI, ZabbixAPIException
import re
import datetime
import time
from colorclass import Color, Windows
from terminaltables import SingleTable
import sys
import os


dict_devices = {}
platform = sys.platform


def calculation_average_values(host_id, item_ids, time_from, time_till):
    """
    Функция для вычесления средних значений потерь и задержек до объекта определённых временными рамками
    time_from, time_till. time_till - конец временного интервала,  time_from - начало временного интервала.
    Function for calculating the average values of losses and delays to an object defined by time frames
    time_from, time_till. time_till - the end of the time interval, time_from - the beginning of the time interval.
    :param host_id:
    :param item_ids:
    :param time_from:
    :param time_till:
    :return: loss_avg, delay_avg
    """
    # print(host_id,item_ids)
    loss = []
    delay = []
    for key, value in item_ids.items():
        # print(key, value)
        # получаем данные для хоста за промежуток времени по потерям
        # we get data for the host over a period of time on losses
        if re.search('loss', key) != None:
            h = z.history.get(hostid=host_id, history=0, itemids=int(value), time_from=time_from, time_till=time_till)
            # print(h)
            for i in h:
                loss.append(float(i.get('value')))
        # получаем данные для хоста за промежуток времени по задержкам
        # we get data for the host over a period of time on delays
        elif re.search('delay', key) != None:
             h = z.history.get(hostid=host_id, history=0, itemids=int(value), time_from=time_from, time_till=time_till)
             # print(h)
             for i in h:
                delay.append(float(i.get('value')))
    loss_avg = round(sum(loss) / len(loss), 1)
    delay_avg = round(sum(delay) / len(delay) * 1000, 1)
    #print(loss_avg, delay_avg)
    return loss_avg, delay_avg


def get_loss_delay(hostname, host_id, time_from, time_till):
    """
    Функция для получения значений потерь и задержек
    Function for getting loss and delay values
    :param hostname:
    :param host_id:
    :param time_from:
    :param time_till:
    :return: loss_avg, delay_avg
    """
    # print(host_id)
    items = z.item.get(hostids=host_id, output=['name'])
    # print(items)
    # print(h)
    item_ids = {}
    """
    Заполняем словарь парами "имя значения":"id этого значения" 
    пример выходных данных {'Packet loss {$SITE}': '1074741', 'Packets delay {$SITE}': '1074742'} 
    We fill in the dictionary with pairs "value name": "id of this value"
    sample output - {'Packet loss {$SITE}': '1074741', 'Packets delay {$SITE}': '1074742'} 
    """
    for item in items:
        # print(hostname, item.get('name'), item.get('itemid'))
        item_ids[item.get('name')] = item.get('itemid')
    # print(item_ids)
    loss_avg, delay_avg = calculation_average_values(host_id, item_ids, time_from, time_till)
    return loss_avg, delay_avg


def create_table(dict_devices):
    """
    Функция для создания отрисовки таблицы
    Function for creating a table
    """
    table_data = []
    table_data_temp =[]
    hostname = "{{{0}}}{1}{{/{0}}}".format("autoyellow", "HOSTNAME")
    loss = "{{{0}}}{1}{{/{0}}}".format("autoyellow", "AVERAGE LOSS 15 min")
    delay = "{{{0}}}{1}{{/{0}}}".format("autoyellow", "AVERAGE DELAY 15 min")
    table_data.append([Color(hostname), Color(loss), Color(delay)])
    for key in dict_devices:
        hostname = key
        loss = dict_devices.get(key)[0]
        delay = '{0} ms'.format(dict_devices.get(key)[1])

        if loss == 0:
            loss = 0
            hostname = "{{{0}}}{1}{{/{0}}}".format("autogreen", hostname)
            loss = "{{{0}}}{1}%{{/{0}}}".format("autogreen", loss)
            delay = "{{{0}}}{1}{{/{0}}}".format("autogreen", delay)
            table_data_temp.append([Color(hostname), Color(loss), Color(delay)])

        elif  0 < loss < 20:
            hostname = "{{{0}}}{1}{{/{0}}}".format("autogreen", hostname)
            loss = "{{{0}}}{1}%{{/{0}}}".format("autocyan", loss)
            delay = "{{{0}}}{1}{{/{0}}}".format("autogreen", delay)
            table_data_temp.append([Color(hostname), Color(loss), Color(delay)])

        else:
            hostname = "{{{0}}}{1}{{/{0}}}".format("autored", hostname)
            loss = "{{{0}}}{1}%{{/{0}}}".format("autored", loss)
            delay = "{{{0}}}{1}{{/{0}}}".format("autored", delay)
            table_data_temp.append([Color(hostname), Color(loss), Color(delay)])

    for i in sorted(table_data_temp):
        table_data.append(i)

    table_instance = SingleTable(table_data)
    table_instance.inner_heading_row_border = True
    table_instance.inner_row_border = False
    table_instance.justify_columns = {0: 'center', 1: 'center', 2: 'center'}
    return table_instance.table


if __name__ == "__main__":
    while True:
        start = datetime.datetime.now()
        try:
            z = ZabbixAPI(url='https://monitoring.eurochem.ru', user='permogorsky_is@moscow', password='!!QQ11qq')
            # print(z.api_version())
            groups_id = []
            groups = z.hostgroup.get(output=['itemid', 'name'])  # get all host groups on the server

            for group in groups:
                """ 
                If name group matches the pattern, put the group number in the list 'group_id' 
                Если имя группы сщвпадает с регулярным выражением, помещаем номер группы в список 'group_id' 
                """
                if re.search(r'.*witch.*', group["name"]):
                    groups_id.append(group['groupid'])
                    # print(group['groupid'], group['name'])
                    continue

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
                        # print(host.get('name'))
                        if re.search('-Core-', host.get('name')) != None:
                        # print(host)
                            hosts.append(host)
                # print(hosts)
            time_till = time.mktime(datetime.datetime.now().timetuple())
            time_from = time_till - 60 * 15    # 15 minutes
            dict_devices.clear()
            for i in hosts:
                # print(i.get('hostid'),i.get('name'))
                loss_avg, delay_avg = get_loss_delay(i.get('name'), int(i.get('hostid')), time_from, time_till)
                dict_devices[i.get('name')] = [loss_avg, delay_avg]
            # print(dict_devices)

            # print('list groups =', groups_id)
            if "win" in platform:
                Windows.enable(auto_colors=True, reset_atexit=True)  # Enable colors in the windows terminal
            else:
                pass
            os.system("cls||clear")
            print(start)
            print(create_table(dict_devices))
            dict_devices.clear()
        except ZabbixAPIException as e:
            print(e)
        end = datetime.datetime.now()
        delta = "{autored}" + str(end - start) + "{/autored}"
        print(Color(delta))
        time.sleep(30)
