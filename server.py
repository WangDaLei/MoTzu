import tornado
import redis
import json
from random import shuffle, randint
from tornado.netutil import bind_sockets
from tornado.tcpserver import TCPServer
from tornado.ioloop import IOLoop
from tornado.iostream import StreamClosedError
from status_code import (
    STATUS_NEW_GAME,
    STATUS_GAME_OVER,
    STATUS_GET_INIT_CARDS,
    STATUS_EXCHANGE_CARDS,
    STATUS_PLAY_CARD,
    STATUS_GET_CARD,
    STATUS_WAIT_FOR_INIT_CARDS,
    STATUS_WAIT_FOR_EXCHANGE_CARDS,
    STATUS_WAIT_FOR_GET_CARD,
    RESPONSE_GAME_OVER,
    RESPONSE_GAME_OVER_NO_CARD,
    RESPONSE_PLAY_CARD,
    RESPONSE_GET_SELF_CARD,
    RESPONSE_GET_OTHER_CARD
)


class EchoServer(TCPServer):

    def __init__(self):
        super(EchoServer, self).__init__()
        self.redis = self.get_redis_connection()

    def hset_redis(self, name, key, value):
        self.redis.hset(name, key, json.dumps(value))

    def hget_redis(self, name, key):
        if self.redis.hget(name, key):
            return json.loads(self.redis.hget(name, key))
        else:
            return None

    def set_redis(self, key, value):
        self.redis.set(key, json.dumps(value))

    def get_redis(self, key):
        if self.redis.get(key):
            return json.loads(self.redis.get(key))
        else:
            return None

    def get_redis_connection(self):
        pool = redis.ConnectionPool(
            host='127.0.0.1', port=6379
        )
        r = redis.Redis(connection_pool=pool)
        return r

    def get_current_table(self):
        seat_num = self.get_redis('seat_num')
        return seat_num if seat_num else 1

    def get_current_num(self):
        table_num = self.get_redis('table_num')
        return table_num if table_num else 1

    def apply_table(self):
        table_num = self.get_redis('table_num')
        seat_num = self.get_redis('seat_num')

        if not table_num:
            table_num = 1
            seat_num = 1
        else:
            if seat_num == 4:
                table_num += 1
                seat_num = 1
            else:
                seat_num += 1

        self.set_redis('table_num', table_num)
        self.set_redis('seat_num', seat_num)
        return table_num, seat_num

    def shuffle_cards(self, table_number):
        # 洗牌并给客户端分发初始的牌
        table = str(table_number)

        cards_list = [i + 1 for i in range(108)]
        shuffle(cards_list)

        cards = dict()
        for i in range(53):
            key = str(i % 4 + 1)
            if key not in cards:
                cards[key] = [cards_list[i]]
            else:
                cards[key].append(cards_list[i])

        self.hset_redis('cards', table, cards)
        self.hset_redis('left_cards', table, cards_list[53:])

    def pop_card(self, table, num, card_list):
        for one in card_list:
            one = int(one)
            cards = self.hget_redis('cards', str(table))
            if one in cards[str(num)]:
                cards[str(num)].remove(one)
                self.hset_redis('cards', str(table), cards)
            else:
                print(str(one) + "is not in list")

    def push_card(self, table, num, card_list):
        cards = self.hget_redis('cards', str(table))
        for one in card_list:
            cards[str(num)].append(int(one))
        self.hset_redis('cards', str(table), cards)

    def exchange_cards(self, table, table_exchange_cards, exchange_mode):
        for one in table_exchange_cards:
            self.pop_card(str(table), one, table_exchange_cards[one])

        for one in table_exchange_cards:
            exchange_num = (int(one) + exchange_mode) % 4
            if exchange_num == 0:
                exchange_num = 4
            self.push_card(str(table), str(exchange_num), table_exchange_cards[one])

        self.hset_redis('table_exchange_status', table, 1)

    async def response_shuffle_cards(self, stream):
        table_number, seat_number = self.apply_table()
        if seat_number == 4:
            self.shuffle_cards(table_number)
        await stream.write(
            bytes(
                str(table_number) + " " + str(seat_number),
                encoding="utf8"
            )
        )

    async def response_init_cards(self, stream, data_list):
        table = data_list[1]
        num = data_list[2]
        current_table = self.get_current_table()
        current_num = self.get_current_num()
        cards = self.hget_redis('cards', table)
        if not cards:
            await stream.write(
                bytes(STATUS_WAIT_FOR_INIT_CARDS, encoding="utf8")
            )
        else:
            if current_table > int(table) or \
               (current_table == int(table) and current_num == 4):
                cards = str(cards[str(num)])
                await stream.write(bytes(cards, encoding="utf8"))
            else:
                await stream.write(
                    bytes(STATUS_WAIT_FOR_INIT_CARDS, encoding="utf8")
                )

    async def response_exchange_cards(self, stream, data_list):
        table = data_list[1]
        num = data_list[2]

        exchange_mode = 0
        table_exchange_mode = self.hget_redis('table_exchange_mode', table)
        table_exchange_cards = self.hget_redis('table_exchange_cards', table)
        table_exchange_status = self.hget_redis('table_exchange_status', table)

        if table_exchange_mode:
            exchange_mode = table_exchange_mode
        else:
            exchange_mode = randint(1, 3)
            self.hset_redis('table_exchange_mode', table, exchange_mode)

        if not table_exchange_cards:
            table_exchange_cards = {}
            table_exchange_cards[str(num)] = [data_list[i + 3] for i in range(3)]
            self.hset_redis('table_exchange_cards', table, table_exchange_cards)

        else:
            if str(num) not in table_exchange_cards:
                table_exchange_cards[str(num)] = [data_list[i + 3] for i in range(3)]
                self.hset_redis('table_exchange_cards', table, table_exchange_cards)

            if len(table_exchange_cards) == 4 and table_exchange_status != 1:
                self.exchange_cards(table, table_exchange_cards, exchange_mode)

        if table_exchange_status != 1:
            await stream.write(bytes(STATUS_WAIT_FOR_EXCHANGE_CARDS, encoding="utf8"))

        else:
            exchange_num = (int(num) + 4 - exchange_mode) % 4
            if exchange_num == 0:
                exchange_num = 4
            exchang_list = table_exchange_cards[str(exchange_num)]
            exchang_list = [str(one) for one in exchang_list]
            await stream.write(bytes(','.join(exchang_list), encoding="utf8"))

    async def response_play_card(self, stream, data_list):
        table = data_list[1]
        num = data_list[2]
        card = int(data_list[3])
        cards = self.hget_redis('cards', table)
        cards[str(num)].remove(card)
        self.hset_redis('cards', table, cards)
        self.hset_redis('table_last_hand', table, num)
        self.hset_redis('table_last_turn', table, card)

        get_status_list = [i + 1 for i in range(4) if i + 1 != int(num)]
        self.hset_redis('table_last_hand_status', table, get_status_list)
        await stream.write(bytes(RESPONSE_PLAY_CARD, encoding="utf8"))

    async def response_get_card(self, stream, data_list):
        table = data_list[1]
        num = data_list[2]

        left_cards = self.hget_redis('left_cards', table)
        table_last_hand_status = self.hget_redis('table_last_hand_status', table)

        if not table_last_hand_status:
            if not left_cards:
                await stream.write(bytes(RESPONSE_GAME_OVER_NO_CARD, encoding="utf8"))
            else:
                card = left_cards[0]
                left_cards = left_cards[1:]
                table_last_hand = self.hget_redis('table_last_hand', table)
                table_last_hand = int(table_last_hand) if table_last_hand else 0
                table_last_hand += 1
                if table_last_hand == 5:
                    table_last_hand = 1
                    # self.hset_redis('table_last_hand', table, table_last_hand)
                if int(num) == table_last_hand:
                    cards = self.hget_redis('cards', table)
                    cards[str(num)].append(card)
                    self.hset_redis('cards', table, cards)
                    self.hset_redis('left_cards', table, left_cards)
                    res_str = RESPONSE_GET_SELF_CARD + " " + str(card)
                    await stream.write(bytes(res_str, encoding="utf8"))
                else:
                    await stream.write(bytes(STATUS_WAIT_FOR_GET_CARD, encoding="utf8"))
        else:
            num = int(num)
            table_last_turn = self.hget_redis('table_last_turn', table)
            if table_last_hand_status and num in table_last_hand_status:
                table_last_hand_status.remove(num)
                self.hset_redis(
                    'table_last_hand_status', table, table_last_hand_status)
                res_str = RESPONSE_GET_OTHER_CARD + " " + str(table_last_turn)
                await stream.write(bytes(res_str, encoding="utf8"))
            else:
                await stream.write(bytes(STATUS_WAIT_FOR_GET_CARD, encoding="utf8"))

    async def handle_stream(self, stream, address):
        while True:
            try:
                data = await stream.read_until(b"\n")
                data_str = str(data, encoding="utf8")
                data_list = data_str.strip().split(' ')

                if data_list[0] == STATUS_NEW_GAME:
                    # 申请桌号的位置, 随机洗牌
                    await self.response_shuffle_cards(stream)

                elif data_list[0] == STATUS_GET_INIT_CARDS:
                    # 桌满发牌，桌未满等待
                    await self.response_init_cards(stream, data_list)

                elif data_list[0] == STATUS_EXCHANGE_CARDS:
                    # 换三张
                    await self.response_exchange_cards(stream, data_list)

                elif data_list[0] == STATUS_GAME_OVER:
                    # 有人赢牌 游戏结束
                    # table = data_list[1]
                    # num = data_list[2]
                    await stream.write(bytes(RESPONSE_GAME_OVER, encoding="utf8"))

                elif data_list[0] == STATUS_PLAY_CARD:
                    # 出牌
                    await self.response_play_card(stream, data_list)

                elif data_list[0] == STATUS_GET_CARD:
                    # 给用户推送出的牌
                    await self.response_get_card(stream, data_list)

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
