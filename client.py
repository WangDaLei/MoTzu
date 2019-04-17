
import json
import time
import random
from socket import socket, AF_INET, SOCK_STREAM


class Client():
    def __init__(self):
        super(Client, self).__init__()
        self.cli = self.get_socket_cli()
        self.list_pai = []

    def get_socket_cli(self):
        cli = socket(AF_INET, SOCK_STREAM)
        cli.connect(("localhost", 8888))
        return cli

    def get_table(self):
        data = b"1 Hello World\n"

        self.cli.send(data)
        recv = self.cli.recv(1024)
        str_recv = str(recv, encoding="utf8")
        print(str_recv)
        self.table = str_recv.split(' ')[0]
        self.num = str_recv.split(' ')[1]

    def start(self):
        while True:
            data = b'2 1 %b %b\n' % (str.encode(self.table), str.encode(self.num))
            self.cli.send(data)
            recv = self.cli.recv(1024)
            str_recv = str(recv, encoding="utf8")
            if str_recv == '401':
                time.sleep(1)
            else:
                list_recv = json.loads(str_recv)
                self.list_pai = sorted(list_recv)
                break

    def choose_from_pai(self, pai_list):
        rm_list = []
        for i in range(3):
            len_pai = len(pai_list)
            pos = random.randint(0, len_pai - 1)
            rm_list.append(pai_list[pos])
            pai_list.remove(pai_list[pos])
        return rm_list

    def make_policy_decision(self, policy_type, hand_pai):
        if policy_type == 'exchange':
            hand_pai = sorted(hand_pai.items(), key=lambda item: len(item[1]))
            for key in hand_pai:
                if len(hand_pai[key]) >= 3:
                    three = self.choose_from_pai(hand_pai[key])
                    return key, three
        else:
            pass

    def trible_charge(self, list_pai):
        tong_pai = []
        tiao_pai = []
        wan_pai = []
        for one in list_pai:
            one -= 1
            num = ((one % 36) // 4) + 1
            if one // 36 == 0:
                tong_pai.append(num)
            elif one // 36 == 1:
                tiao_pai.append(num)
            else:
                wan_pai.append(num)
        hand_pai = {}
        hand_pai['tong'] = tong_pai
        hand_pai['tiao'] = tiao_pai
        hand_pai['wan'] = wan_pai
        key, three = self.make_policy_decision(list_pai, hand_pai)

    def decide(self):
        str_pai = ''
        for one in self.list_pai:
            one -= 1
            num = ((one % 36) // 4) + 1
            if one // 36 == 0:
                str_pai += str(num) + "@ "
            elif one // 36 == 1:
                str_pai += str(num) + '| '
            else:
                str_pai += str(num) + 'W '
        print(str_pai)


if __name__ == '__main__':
    client = Client()
    client.get_table()
    client.start()
    client.decide()
