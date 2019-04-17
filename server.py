import tornado
import MySQLdb
from random import shuffle
from tornado.netutil import bind_sockets
from tornado.tcpserver import TCPServer
from tornado.ioloop import IOLoop
from tornado.iostream import StreamClosedError


class EchoServer(TCPServer):

    def __init__(self):
        super(EchoServer, self).__init__()
        self.cursor = self.get_database_cursor()
        self.pai = {}
        self.left_pai = {}

    def get_database_cursor(self):
        db = MySQLdb.connect("localhost", "root", "123456", "stock", charset='utf8')
        cursor = db.cursor()
        return cursor

    def get_current_table(self):
        sql = "select * from majiang_config where name = 'table';"
        self.cursor.execute(sql)
        table = self.cursor.fetchone()[2]
        return table

    def get_current_num(self):
        sql = "select * from majiang_config where name = 'count';"
        self.cursor.execute(sql)
        num = self.cursor.fetchone()[2]
        return num

    def update_current_table(self, value):
        sql = "lock table majiang_config write; " +\
              "update majiang_config set value = '%s' where name = 'table'; " % (value) +\
            "unlock tables;"
        self.cursor.execute(sql)

    def update_current_num(self, value):
        sql = "lock table majiang_config write; " +\
              "update majiang_config set value = '%s' where name = 'count'; " % (value) +\
              "unlock tables;"
        self.cursor.execute(sql)

    def apply_table(self):
        table = self.get_current_table()
        num = self.get_current_num()
        temp1 = num
        temp2 = table
        if num == 4:
            self.update_current_num(1)
            self.update_current_table(table + 1)
            temp1 = 1
            temp2 += 1
        else:
            self.update_current_num(num + 1)
            temp1 += 1
        return temp1, temp2

    def deal_cards(self, table):
        table = str(table)
        pais = [i + 1 for i in range(108)]
        shuffle(pais)
        num_1 = []
        num_2 = []
        num_3 = []
        num_4 = []
        for i in range(53):
            if i % 4 == 0:
                num_1.append(pais[i])
            elif i % 4 == 1:
                num_2.append(pais[i])
            elif i % 4 == 2:
                num_3.append(pais[i])
            else:
                num_4.append(pais[i])
        left_pai = pais[53:]
        self.left_pai[table] = left_pai
        table_pais = {}
        table_pais['1'] = num_1
        table_pais['2'] = num_2
        table_pais['3'] = num_3
        table_pais['4'] = num_4
        self.pai[table] = table_pais

    async def handle_stream(self, stream, address):
        while True:
            try:
                data = await stream.read_until(b"\n")
                data_str = str(data, encoding="utf8")
                data_list = data_str.strip().split(' ')
                print(data_list)
                if data_list[0] == '1':
                    temp1, temp2 = self.apply_table()
                    if temp1 == 4:
                        self.deal_cards(temp2)
                    await stream.write(bytes(str(temp2) + " " + str(temp1), encoding="utf8"))
                elif data_list[0] == '2':
                    if data_list[1] == '1':
                        table = data_list[2]
                        num = data_list[3]
                        current_table = self.get_current_table()
                        current_num = self.get_current_num()
                        if current_table > int(table) or \
                           (current_table == int(table) and current_num == 4):
                            pais = str(self.pai[str(table)][str(num)])
                            await stream.write(bytes(pais, encoding="utf8"))
                        else:
                            await stream.write(bytes("401", encoding="utf8"))
                    else:
                        pass
                    # await stream.write(bytes(str(table) + " " + str(num), encoding="utf8"))
                else:
                    pass
            except StreamClosedError:
                break

if __name__ == '__main__':
    sockets = bind_sockets(8888)
    tornado.process.fork_processes(0)
    server = EchoServer()
    server.add_sockets(sockets)
    IOLoop.current().start()
