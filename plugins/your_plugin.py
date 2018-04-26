# -*- coding: utf-8 -*-
import time
import traceback
import struct

#import can
from simplecannet import client
import cantools

from logging import getLogger

from Doctopus.Doctopus_main import Check, Handler

log = getLogger('Doctopus.plugins')


class MyCheck(Check):
    def __init__(self, configuration):
        super(MyCheck, self).__init__(configuration=configuration)
        self.conf = configuration['user_conf']['check']
        self.init()

    def init(self):
        """
        init tcp client
        :return: 
        """
        while True:
            try:
                self.db = cantools.db.load_file(self.conf['dbc_path'])
                #self.necessary_frame_id_list = self.collect_frame_id()
                self.necessary_frame_id_list = self.conf['frame_ids']
                self.unnecessary_signals = self.conf['signals']
                self.bus = client.TcpcanBus(port=self.conf['port'], ip=self.conf['ip'])
                self.count = 0 # init count for count times of recv data
                break # only build a tcp connnection, can go to next step

            except Exception as e:
                log.error(e)
                log.debug("can't init whole client")

    def collect_frame_id(self):
        """
        collect frame id list we need from dbc file
        :return:  list
        """
        messages = self.db.messages
        frame_id_list = [ frame.frame_id for frame in messages]
        return frame_id_list

    def bus_recv(self):
        """receive all data we need in the bus"""
        frames_id_list = list(self.necessary_frame_id_list)  # clone a new list
        log.debug(frames_id_list)
        data_original = []
        # collect all frames in frames_id_list
        while frames_id_list:
            frame = self.bus.recv()
            if frame:
                log.debug(frame.arbitration_id)
                if frame.arbitration_id in frames_id_list:
                    data_original.append(frame)
                    frames_id_list.remove(frame.arbitration_id)

        log.debug("receive enough frame~！！！！！！！！！！！！！！！！！！！")
        log.debug(self.necessary_frame_id_list)
        return data_original

    def dbc_convert(self, can_data):
        """
        convert can_data to right format 
        :param can_data: 
        :return: list
        """
        data_convert_dicts = {}

        for data in can_data:
            frame_message = self.db.decode_message(data.arbitration_id, data.data)
            data_convert_dicts.update(frame_message)

        if self.unnecessary_signals:
            for k in self.unnecessary_signals:
                data_convert_dicts.pop(k)    #remove unnecessary signals

        log.debug("=====================>data_original_dicts:")
        log.debug(data_convert_dicts)
        return data_convert_dicts

    @staticmethod
    def int_to_float(value):
        """ 
        turn int to double float
        """
        temp_value = struct.pack("I", int(value*1000))
        data = struct.unpack("i", temp_value)

        return data[0]/1000

    def format_dict(self, original_dicts):
        """
        turn data value to right type(int => float )
        :param dicts: 
        :return: dict
        """
        # data_dict = {}
        log.debug(original_dicts)
        for k, v in original_dicts.items():
            original_dicts[k] = self.int_to_float(v)
        original_dicts['bskl_cba_ap'] /= 10

        return  original_dicts

    def handle_warning_dict(self, data_dicts):
        """
        handle warning dict , convert to a string
        :param data_dicts: 
        :return: 
        """
        # 0: error
        # 1: normal
        # 2: don't exit
        warning_dicts = {
         'ok_gas': "气体报警;",
         'ok_fire': "火警报警;",
        }
        warning_string = ''
        warning_message = {}

        for k in warning_dicts.keys() & data_dicts.keys():
            if data_dicts[k] == 0:
                warning_string = warning_string + warning_dicts[k]

            # data_dicts.pop(k) # remove key
        warning_message = {'warning': warning_string }

        data_dicts.update(warning_message)

        return data_dicts

    def handle_dict(self, data_dicts):
        """
        
        :param data_dicts: original data dicts
        :return: handled data_dicts
        """
        status_dict = {0: 'dummy for always allowed events',
                       1: 'wait until all p5 tasks have been loaded',
                       2: 'wait until POI has loaded DEEF-info',
                       4: 'wait for SYS-Parameters loaded from AFBI',
                       10: 'wait till date and time entered',
                       13: 'wait for reboot after fatal error',
                       14: 'wait for shutdown of P7 after power fail',
                       50: 'wait for operator after fata error in sys_par',
                       99: 'TCC Event OnInit',
                       100: 'monitoring (=> MANUAL TCC OnMonToMan = 100)', # stop
                       105: 'wait for calib. P730 completed',
                       110: 'wait for dialog finished',
                       114: 'wait until engine is dismounted from host',
                       115: 'wait until engine is mounted to host',
                       116: 'wait of customer spec. normn.and val.',
                       120: 'wait for SYS updated from AFBI',
                       130: 'check if new Test needs to be Loaded',
                       131: 'wait for TST updated and checked from AFBI',
                       140: 'wait for TRRFILENAME entered',
                       141: 'wait for TRR_APPEND_CHECK completed (OnSelectResult)',
                       150: 'wait for INPUT_ENGINE_PARAMETER completed (OnUUTDialog)',
                       170: 'wait for PTCC_startup completed',
                       171: 'wait for PTCC_reaction completed',
                       175: 'wait for Meas.devices INIT completed',
                       190: 'wait for all emergency conditions clear (from MONITOR: OnBeqinOfTestSequence)',

                       200: 'manual',  # run
                       201: 'reload TST (from ReloadTest: OnBeginOfTestSequence)',
                       204: 'wait for till stillstandsmenu is ready',
                       210: 'wait for parameter online change completed',
                       220: 'wait for SOL, MES, PRO completed',
                       240: 'wait for enddialog entered',
                       241: 'wait for resultdialog finished',
                       242: 'wait for TRR_APPEND_CHECK completed',
                       250: 'wait for INPUT_ENGINE_PARAMETER completed',
                       290: 'wait for post_mortem finished',
                       300: 'manual virtual or remote',
                       301: 'manual with BNC-Inputs ABS/ADD',
                       500: 'automatic',    # run
                       509: 'check for pending dialogs',
                       510: 'coldrun after test finished',
                       511: 'final coldrun after go to monitor',
                       515: 'wait for PTCC shutdown finished (OnShutDown)',
                       517: 'wait for PTCC reaction completed',
                       520: 'wait for enddialog finished',
                       530: 'wait for endprotokoll printed or stored',
                       531: 'wait for endprotokoll stored',
                       532: 'wait for endprotokoll printed (OnManToMon)',
                    }

        status_number = data_dicts['status']
        speed = data_dicts.get('d_spddig_n', 70)

        #  set status is 1 if auto
        if status_number == 500 or (status_number == 200 and speed >= 600):
            data_dicts['status'] = 1.0
        else:
            data_dicts['status'] = 0.0

        # update warning information in data_dicts
        if status_number in status_dict.keys():
            warning = {'messages': status_dict[status_number]}
        else:
            warning = {'messages': 'unkown status code {}'.format(status_number)}

        data_dicts.update(warning)

        return data_dicts

    def reconnect(self):
        """
        reconnect to tcp_can
        :return: 
        """
        self.bus.reconnect()

    def user_check(self):
        """

        :param command: user defined parameter.
        :return: the data you requested.
        """
        log.debug("begin~~~~~~~~~~~~~~~~~~~~~~!!!!!!!!!!!!!!!!")
        # trying recv data:
        try:
            # time.sleep(1)
            # when self. count=10, send data to low 10Hz to 1Hz
            
            data_original = self.bus_recv()

            data_convert_dicts = self.dbc_convert(data_original)

            data_dicts = self.format_dict(data_convert_dicts)

            data_dicts_handle = self.handle_dict(data_dicts)

            final_data_dicts = self.handle_warning_dict(data_dicts_handle)
            #final_data_dicts = data_dicts_handle

            log.debug('data dict is {}'.format(final_data_dicts))
            
            if self.count >= 10:
                self.count = 0
                yield final_data_dicts
            else:
                self.count = self.count + 1


        except Exception as e:
            log.error(e)
            traceback.print_exc()
            self.reconnect()


class MyHandler(Handler):
    def __init__(self, configuration):
        super(MyHandler, self).__init__(configuration=configuration)

    def user_handle(self, raw_data):
        """
        用户须输出一个dict，可以填写一下键值，也可以不填写
        timestamp， 从数据中处理得到的时间戳（整形?）
        tags, 根据数据得到的tag
        data_value 数据拼接形成的 list 或者 dict，如果为 list，则上层框架
         对 list 与 field_name_list 自动组合；如果为 dict，则不处理，认为该数据
         已经指定表名
        measurement 根据数据类型得到的 influxdb表名

        e.g:
        list:
        {'data_value':[list] , required
        'tags':[dict],        optional
        'table_name',[str]   optional
        'timestamp',int}      optional

        dict：
        {'data_value':{'fieldname': value} , required
        'tags':[dict],        optional
        'table_name',[str]   optional
        'timestamp',int}      optional

        :param raw_data: 
        :return: 
        """
        # exmple.
        # 数据经过处理之后生成 value_list
        log.debug('%s', raw_data)
        data_value_list = raw_data
        tags = {'eqpt_no': '32220000365'}

        # user 可以在handle里自己按数据格式制定tags
        user_postprocessed = {'data_value': data_value_list,
                              'tags': tags}
        yield user_postprocessed
