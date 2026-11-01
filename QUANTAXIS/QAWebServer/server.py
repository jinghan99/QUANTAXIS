# coding:utf-8
#
# The MIT License (MIT)
#
# Copyright (c) 2016-2018 yutiansut/QUANTAXIS
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
import asyncio
import os
import sys

import tornado
from QUANTAXIS import __version__
from QUANTAXIS.QAUtil.QASetting import QASETTING
from QUANTAXIS.QAWebServer.basehandles import QABaseHandler
from QUANTAXIS.QAWebServer.commandhandler import (CommandHandler,
                                                  CommandHandlerWS,
                                                  RunnerHandler)
from QUANTAXIS.QAWebServer.schedulehandler import (QAScheduleQuery,
                                                   QASchedulerHandler,
                                                   init_scheduler)
from QUANTAXIS.QAWebServer.qifiserver import QAQIFI_Handler, QAQIFIS_Handler, QAQIFIS_REALTIME_Handler
from tornado.options import (define, options, parse_command_line,
                             parse_config_file)
from tornado.web import Application, RequestHandler, authenticated


class INDEX(QABaseHandler):

    def get(self):
        self.write(
            {
                'status': 200,
                'message': 'This is a welcome page for quantaxis backend',
                'url': [item[0] for item in handlers]
            }
        )


class QAUserhander(QABaseHandler):
    def get(self):
        self.write({'status': 200, 'result':{'user_cookie': 'xx'}})


class Readiness(QABaseHandler):
    def get(self):
        try:
            client = QASETTING.client
            client.admin.command('ping')
            database = client.quantaxis
            counts = {name: database[name].estimated_document_count()
                      for name in ('stock_day', 'stock_min', 'index_day', 'history')}
            self.write({
                'status': 'ready',
                'environment': os.getenv('QUANTAXIS_ENV', 'dev'),
                'debug': self.application.settings.get('debug', False),
                'autoreload': self.application.settings.get('autoreload', False),
                'mongodb_server': list(client.address),
                'mongodb_database': database.name,
                'data_status': 'available' if counts['stock_day'] else 'empty',
                'counts': counts,
                'scheduler_collection': os.getenv('QA_SCHEDULER_COLLECTION', 'jobs'),
            })
        except Exception as exc:
            self.set_status(503)
            self.write({'status': 'unavailable', 'error_type': type(exc).__name__})

#term_manager = SingleTermManager(shell_command=['bash'])
handlers = [
    (r"/readiness", Readiness),
    (r"/",
     INDEX),
    (r"/command/run",
     CommandHandler),
    (r"/command/runws",
     CommandHandlerWS),
    (r"/command/runbacktest",
     RunnerHandler),
    (r"/scheduler/map/?", QASchedulerHandler),
    (r"/scheduler/query", QAScheduleQuery),
    (r"/qifi", QAQIFI_Handler),
    (r"/qifis", QAQIFIS_Handler),
    (r"/qifirealtime", QAQIFIS_REALTIME_Handler),
    (r"/user", QAUserhander)

]


def main():
    asyncio.set_event_loop(asyncio.new_event_loop())
    define("port", default=18089, type=int, help="服务器监听端口号")

    define("address", default='0.0.0.0', type=str, help='服务器地址')
    define("content", default=[], type=str, multiple=True, help="控制台输出内容")

    parse_command_line()
    port = options.port
    address = options.address
    scheduler = init_scheduler()

    start_server(handlers, address, port)


def start_server(handlers, address='0.0.0.0', port=18089):
    development = os.getenv('QUANTAXIS_ENV', 'dev') != 'prod'
    apps = Application(
        handlers=handlers,
        debug=development,
        autoreload=development,
        compress_response=True
    )
    
    print('========WELCOME QUANTAXIS_WEBSERVER 2.0 ============')
    print('QUANTAXIS VERSION: {}'.format(__version__))
    print('QUANTAXIS WEBSERVER is Listening on: http://{}:{}'.format(address, port))
    print('请打开浏览器/使用JavaScript等来使用该后台, 并且不要关闭当前命令行窗口')
    apps.listen(port, address=address)

    tornado.ioloop.IOLoop.current().start()


if __name__ == '__main__':
    main()
