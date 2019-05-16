import tornado
import MySQLdb
import redis
import json
from random import shuffle, randint
from tornado.netutil import bind_sockets
from tornado.tcpserver import TCPServer
from tornado.ioloop import IOLoop
from tornado.iostream import StreamClosedError


class EchoServer(TCPServer):

    def __init__(self):
        super(EchoServer, self).__init__()
        self.db, self.cursor = self.get_database_cursor()
        self.redis = self.get_redis_connection()

    def get_redis_connection(self):
        pool = redis.ConnectionPool(
            host='127.0.0.1', port=6379
        )
        r = redis.Redis(connection_pool=pool)
        return r

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

        self.redis.hset('cards', table, json.dumps({}))
        # self.cards[table] = {}
        for i in range(4):
            cards = json.loads(self.redis.hget('cards', table))
            cards[str(i + 1)] = []
            self.redis.hset('cards', table, json.dumps(cards))
            # self.cards[table][str(i + 1)] = []

        for i in range(53):
            cards = json.loads(self.redis.hget('cards', table))
            cards[str(i % 4 + 1)].append(cards_list[i])
            self.redis.hset('cards', table, json.dumps(cards))
            # self.cards[table][str(i % 4 + 1)].append(cards_list[i])

        self.redis.hset('left_cards', table, json.dumps(cards_list[53:]))
        self.redis.hset('table_last_turn', table, json.dumps(1))
        self.redis.hset('table_last_turn', table, json.dumps([2, 3, 4]))
        # self.table_last_hand_status[str(table)] = [2, 3, 4]

    def pop_card(self, table, num, pai_list):
        for one in pai_list:
            one = int(one)
            cards = json.loads(self.redis.hget('cards', str(table)))
            if one in cards[str(num)]:
                cards[str(num)].remove(one)
                self.redis.hset('cards', str(table), json.dumps(cards))
            else:
                print(str(one) + "is not in list")

    def push_card(self, table, num, pai_list):
        cards = json.loads(self.redis.hget('cards', str(table)))
        for one in pai_list:
            cards[str(num)].append(int(one))
        self.redis.hset('cards', str(table), json.dumps(cards))

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
                        cards = self.redis.hget('cards', table)
                        if not cards:
                            await stream.write(bytes("401", encoding="utf8"))
                        else:
                            cards = json.loads(cards)
                            if current_table > int(table) or \
                               (current_table == int(table) and current_num == 4):
                                cards = str(cards[str(num)])
                                await stream.write(bytes(cards, encoding="utf8"))
                            else:
                                await stream.write(bytes("401", encoding="utf8"))
                    elif data_list[1] == '2':
                        table = data_list[2]
                        num = data_list[3]
                        order = 0
                        table_turn_order = self.redis.hget('table_turn_order', table)
                        table_turn_pai = self.redis.hget('table_turn_pai', table)
                        table_turn_status = self.redis.hget('table_turn_status', table)

                        if table_turn_order:
                            order = table_turn_order
                        else:
                            rd = randint(1, 3)
                            self.redis.hset('table_turn_order', table, rd)
                            order = rd
                        if not table_turn_pai:
                            temp = {}
                            temp[str(num)] = [data_list[4], data_list[5], data_list[6]]
                            self.redis.hset('table_turn_pai', table, json.dumps(temp))
                        else:
                            table_turn_pai = json.loads(table_turn_pai)
                            if str(num) not in table_turn_pai:
                                temp = {str(num): [data_list[4], data_list[5], data_list[6]]}
                                self.redis.hset('table_turn_pai', table, json.dumps(temp))

                            if len(table_turn_pai) == 4 and\
                                (not table_turn_status or
                                 json.loads(table_turn_status) != 1):
                                for one in table_turn_pai:
                                    self.pop_card(
                                        str(table), one, table_turn_pai[one])
                                if order == 1:
                                    for one in table_turn_pai:
                                        temp = int(one)
                                        temp += 1
                                        if temp == 5:
                                            temp = 1
                                        self.push_card(
                                            str(table), str(temp),
                                            table_turn_pai[one])
                                elif order == 2:
                                    for one in table_turn_pai:
                                        temp = int(one)
                                        temp += 2
                                        if temp > 4:
                                            temp -= 4
                                        self.push_card(
                                            str(table), str(temp),
                                            table_turn_pai[one])
                                else:
                                    for one in table_turn_pai:
                                        temp = int(one)
                                        temp -= 1
                                        if temp == 0:
                                            temp += 4
                                        self.push_card(
                                            str(table), str(temp),
                                            table_turn_pai[one])
                                self.redis.hset('table_turn_status', table, json.dumps(1))
                                # self.table_turn_status[str(table)] = 1

                        if not table_turn_status or\
                           json.loads(table_turn_status) != 1:
                            await stream.write(bytes("402", encoding="utf8"))
                        else:
                            if order == 1:
                                temp = int(num)
                                temp -= 1
                                if temp == 0:
                                    temp += 4
                                data_list = table_turn_pai[str(temp)]
                                data_list = [str(one) for one in data_list]
                                await stream.write(bytes(','.join(data_list), encoding="utf8"))
                            elif order == 2:
                                temp = int(num)
                                temp += 2
                                if temp > 4:
                                    temp -= 4
                                data_list = table_turn_pai[str(temp)]
                                data_list = [str(one) for one in data_list]
                                await stream.write(bytes(','.join(data_list), encoding="utf8"))
                            else:
                                temp = int(num)
                                temp += 1
                                if temp > 4:
                                    temp -= 4
                                data_list = table_turn_pai[str(temp)]
                                data_list = [str(one) for one in data_list]
                                await stream.write(bytes(','.join(data_list), encoding="utf8"))
                    elif data_list[1] == '3':
                        table = data_list[2]
                        num = data_list[3]
                        await stream.write(bytes("200", encoding="utf8"))
                    elif data_list[1] == '4':
                        table = data_list[2]
                        num = data_list[3]
                        pai = int(data_list[4])
                        cards = json.loads(self.redis.hget('cards', table))
                        cards[str(num)].remove(pai)
                        self.redis.hset('cards', table, json.dumps(cards))
                        self.redis.hset('table_last_hand', table, json.dumps(pai))
                        num = int(num)
                        tmp = [1, 2, 3, 4]
                        tmp.remove(num)
                        self.redis.hset('table_last_hand_status', table, json.dumps(tmp))
                        await stream.write(bytes("201", encoding="utf8"))
                    elif data_list[1] == '5':
                        table = data_list[2]
                        num = data_list[3]
                        left_cards = self.redis.hget('left_cards', table)
                        table_last_hand_status = self.redis.hget('table_last_hand_status', table)
                        if not table_last_hand_status:
                            if not left_cards:
                                await stream.write(bytes("203", encoding="utf8"))
                            else:
                                left_cards = json.loads(left_cards)
                                pai = left_cards[0]
                                left_cards = left_cards[1:]
                                table_last_turn = json.loads(
                                    self.redis.hget('table_last_turn', table))
                                table_last_turn += 1
                                if table_last_turn == 5:
                                    table_last_turn = 1
                                    self.redis.hset('table_last_turn', table, json.dumps(1))
                                num = int(num)
                                if num == table_last_turn:
                                    await stream.write(bytes("206 " + str(pai), encoding="utf8"))
                                else:
                                    await stream.write(bytes("202", encoding="utf8"))
                        else:
                            num = int(num)
                            table_last_hand_status = self.redis.hget(
                                'table_last_hand_status', table)
                            table_last_hand = self.json.loads(
                                self.redis.hget('table_last_hand', table))
                            if table_last_hand_status and num in json.loads(table_last_hand_status)\
                               and not table_last_hand:
                                table_last_hand = json.loads(table_last_hand)
                                table_last_hand_status = json.loads(table_last_hand_status)
                                pai = table_last_hand
                                table_last_hand_status.remove(num)
                                self.redis.hset('table_last_hand_status', table, json.dumps(
                                    table_last_hand_status))
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
