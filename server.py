import tornado
import MySQLdb
from random import shuffle, randint
from tornado.netutil import bind_sockets
from tornado.tcpserver import TCPServer
from tornado.ioloop import IOLoop
from tornado.iostream import StreamClosedError


class EchoServer(TCPServer):

    def __init__(self):
        super(EchoServer, self).__init__()
        self.db, self.cursor = self.get_database_cursor()

        self.cards = {}
        self.left_cards = {}

        self.table_turn_order = {}
        self.table_turn_pai = {}
        self.table_turn_status = {}

        self.table_last_hand = {}
        self.table_last_hand_status = {}

        self.table_last_turn = {}

    def get_database_cursor(self):
        db = MySQLdb.connect("localhost", "root", "123456", "stock", charset='utf8')
        cursor = db.cursor()
        return db, cursor

    def get_current_table(self):
        sql = "select * from majiang_config where name = 'table' limit 1;"
        self.cursor.execute(sql)
        table = self.cursor.fetchone()[2]
        self.db.commit()
        return table

    def get_current_num(self):
        sql = "select * from majiang_config where name = 'count' limit 1;"
        self.cursor.execute(sql)
        num = self.cursor.fetchone()[2]
        print("+++++", num)
        self.db.commit()
        return num

    def apply_table(self):
        sql_table = "select * from majiang_config where name = 'table' for update;"
        sql_seat = "select * from majiang_config where name = 'count' for update;"
        update_sql_table = "update majiang_config set value = '%s' where name = 'table'; "
        update_sql_seat = "update majiang_config set value = '%s' where name = 'count'; "

        cursor = self.db.cursor()
        table_num = 0
        seat_num = 0
        try:
            cursor.execute("set autocommit=0;")
            cursor.execute(sql_table)
            table_num = cursor.fetchone()[2]
            cursor.execute(sql_seat)
            seat_num = cursor.fetchone()[2]
            if seat_num == 4:
                cursor.execute(update_sql_table % (table_num + 1))
                cursor.execute(update_sql_seat % (1))
                seat_num = 1
                table_num += 1
            else:
                cursor.execute(update_sql_seat % (seat_num + 1))
                seat_num += 1
            self.db.commit()
        except Exception as e:
            print(e)
            self.db.rollback()
        return table_num, seat_num

    def shuffle_cards(self, table_number):
        # 洗牌并给客户端分发初始的牌
        table = str(table_number)

        cards_list = [i + 1 for i in range(108)]
        shuffle(cards_list)

        self.cards[table] = {}
        for i in range(4):
            self.cards[table][str(i + 1)] = []

        for i in range(53):
            self.cards[table][str(i % 4 + 1)].append(cards_list[i])

        self.left_cards[table] = cards_list[53:]
        self.table_last_turn[table] = 1
        self.table_last_hand_status[str(table)] = [2, 3, 4]

    def pop_card(self, table, num, pai_list):
        for one in pai_list:
            one = int(one)
            if one in self.cards[str(table)][str(num)]:
                self.cards[str(table)][str(num)].remove(one)
            else:
                print(str(one) + "is not in list")

    def push_card(self, table, num, pai_list):
        for one in pai_list:
            self.cards[str(table)][str(num)].append(int(one))

    async def handle_stream(self, stream, address):
        while True:
            try:
                data = await stream.read_until(b"\n")
                data_str = str(data, encoding="utf8")
                data_list = data_str.strip().split(' ')

                if data_list[0] == '100':
                    # 申请桌号的位置, 随机洗牌
                    table_number, seat_number = self.apply_table()
                    if seat_number == 4:
                        self.shuffle_cards(table_number)
                    await stream.write(
                        bytes(
                            str(table_number) + " " + str(seat_number), encoding="utf8"
                        )
                    )
                elif data_list[0] == '2':
                    if data_list[1] == '1':
                        table = data_list[2]
                        num = data_list[3]
                        current_table = self.get_current_table()
                        current_num = self.get_current_num()
                        print(table)
                        print(num)
                        print(str(table) not in self.cards)
                        print(self.cards)
                        if str(table) not in self.cards:
                            await stream.write(bytes("401", encoding="utf8"))
                        else:
                            if current_table > int(table) or \
                               (current_table == int(table) and current_num == 4):
                                cards = str(self.cards[str(table)][str(num)])
                                await stream.write(bytes(cards, encoding="utf8"))
                            else:
                                await stream.write(bytes("401", encoding="utf8"))
                    elif data_list[1] == '2':
                        table = data_list[2]
                        num = data_list[3]
                        order = 0
                        if str(table) in self.table_turn_order:
                            order = self.table_turn_order[str(table)]
                        else:
                            rd = randint(1, 3)
                            self.table_turn_order[str(table)] = rd
                            order = rd
                        if str(table) not in self.table_turn_pai:
                            temp = {}
                            temp[str(num)] = [data_list[4], data_list[5], data_list[6]]
                            self.table_turn_pai[str(table)] = temp
                        else:
                            if str(num) not in self.table_turn_pai[str(table)]:
                                self.table_turn_pai[str(table)][str(num)] = \
                                    [data_list[4], data_list[5], data_list[6]]

                            if len(self.table_turn_pai[str(table)]) == 4 and\
                                (str(table) not in self.table_turn_status or
                                 self.table_turn_status[str(table)] != 1):
                                for one in self.table_turn_pai[str(table)]:
                                    self.pop_card(
                                        str(table), one, self.table_turn_pai[str(table)][one])
                                if order == 1:
                                    for one in self.table_turn_pai[str(table)]:
                                        temp = int(one)
                                        temp += 1
                                        if temp == 5:
                                            temp = 1
                                        self.push_card(
                                            str(table), str(temp),
                                            self.table_turn_pai[str(table)][one])
                                elif order == 2:
                                    for one in self.table_turn_pai[str(table)]:
                                        temp = int(one)
                                        temp += 2
                                        if temp > 4:
                                            temp -= 4
                                        self.push_card(
                                            str(table), str(temp),
                                            self.table_turn_pai[str(table)][one])
                                else:
                                    for one in self.table_turn_pai[str(table)]:
                                        temp = int(one)
                                        temp -= 1
                                        if temp == 0:
                                            temp += 4
                                        self.push_card(
                                            str(table), str(temp),
                                            self.table_turn_pai[str(table)][one])
                                self.table_turn_status[str(table)] = 1

                        if str(table) not in self.table_turn_status or\
                           self.table_turn_status[str(table)] != 1:
                            await stream.write(bytes("402", encoding="utf8"))
                        else:
                            print("+++++++++++", order)
                            print(self.cards[str(table)])
                            if order == 1:
                                temp = int(num)
                                temp -= 1
                                if temp == 0:
                                    temp += 4
                                data_list = self.table_turn_pai[str(table)][str(temp)]
                                data_list = [str(one) for one in data_list]
                                await stream.write(bytes(','.join(data_list), encoding="utf8"))
                            elif order == 2:
                                temp = int(num)
                                temp += 2
                                if temp > 4:
                                    temp -= 4
                                data_list = self.table_turn_pai[str(table)][str(temp)]
                                data_list = [str(one) for one in data_list]
                                await stream.write(bytes(','.join(data_list), encoding="utf8"))
                            else:
                                temp = int(num)
                                temp += 1
                                if temp > 4:
                                    temp -= 4
                                data_list = self.table_turn_pai[str(table)][str(temp)]
                                data_list = [str(one) for one in data_list]
                                await stream.write(bytes(','.join(data_list), encoding="utf8"))
                    elif data_list[1] == '3':
                        table = data_list[2]
                        num = data_list[3]
                        print(table, num)
                        # check
                        await stream.write(bytes("200", encoding="utf8"))
                        # else:
                        # await stream.write(bytes("210", encoding="utf8"))
                    elif data_list[1] == '4':
                        table = data_list[2]
                        num = data_list[3]
                        pai = int(data_list[4])
                        print("-------------")
                        print(self.cards[str(table)][str(num)])
                        print(pai)
                        print(type(pai))
                        print(pai in self.cards[str(table)][str(num)])
                        self.cards[str(table)][str(num)].remove(pai)
                        self.table_last_hand[str(table)] = pai
                        num = int(num)
                        tmp = [1, 2, 3, 4]
                        tmp.remove(num)
                        self.table_last_hand_status[str(table)] = tmp
                        await stream.write(bytes("201", encoding="utf8"))
                    elif data_list[1] == '5':
                        table = data_list[2]
                        num = data_list[3]
                        print("+++++++")
                        print(len(self.left_cards[str(table)]))
                        print(self.table_last_hand_status)
                        print(self.table_last_hand_status[str(table)])
                        if len(self.table_last_hand_status[str(table)]) == 0:
                            if len(self.left_cards[str(table)]) == 0:
                                await stream.write(bytes("203", encoding="utf8"))
                            else:
                                pai = self.left_cards[str(table)][0]
                                self.left_cards[str(table)] = self.left_cards[str(table)][1:]
                                self.table_last_turn[str(table)] += 1
                                if self.table_last_turn[str(table)] == 5:
                                    self.table_last_turn[str(table)] = 1
                                num = int(num)
                                if num == self.table_last_turn[str(table)]:
                                    await stream.write(bytes("206 " + str(pai), encoding="utf8"))
                                else:
                                    await stream.write(bytes("202", encoding="utf8"))
                        else:
                            num = int(num)
                            print("++++++")
                            print(len(self.left_cards[str(table)]))
                            print(self.table_last_hand_status[str(table)])
                            if num in self.table_last_hand_status[str(table)] and\
                               str(table) in self.table_last_hand:
                                pai = self.table_last_hand[str(table)]
                                self.table_last_hand_status[str(table)].remove(num)
                                await stream.write(bytes("205 " + str(pai), encoding="utf8"))
                            else:
                                await stream.write(bytes("202", encoding="utf8"))
                    else:
                        pass
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
