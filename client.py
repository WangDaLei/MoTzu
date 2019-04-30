
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
            # print(hand_pai)
            for key in range(len(hand_pai)):
                if len(hand_pai[key][1]) >= 3:
                    three = self.choose_from_pai(hand_pai[key][1])
                    return hand_pai[key][0], three
        else:
            pass

    def reverse_by_key(self, key, three):
        num_list = []
        if key == 'tong':
            for one in three:
                min_num = (one - 1) * 4 + 1
                max_num = one + 4
                for pai in self.list_pai:
                    if pai >= min_num and pai <= max_num:
                        self.list_pai.remove(pai)
                        num_list.append(pai)
                        break
        elif key == 'tiao':
            for one in three:
                min_num = (one - 1) * 4 + 1 + 36
                max_num = one + 4 + 36
                for pai in self.list_pai:
                    if pai >= min_num and pai <= max_num:
                        self.list_pai.remove(pai)
                        num_list.append(pai)
                        break
        else:
            for one in three:
                min_num = (one - 1) * 4 + 1 + 72
                max_num = one + 4 + 72
                for pai in self.list_pai:
                    if pai >= min_num and pai <= max_num:
                        self.list_pai.remove(pai)
                        num_list.append(pai)
                        break

        return num_list

    def trible_charge(self):
        self.print_pai()
        tong_pai = []
        tiao_pai = []
        wan_pai = []
        for one in self.list_pai:
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
        key, three = self.make_policy_decision('exchange', hand_pai)
        self.print_pai_by_key(key, three)
        num_list = self.reverse_by_key(key, three)
        print(num_list)

    def print_pai_by_key(self, key, three):
        out_str = ''
        three = [str(i) for i in three]
        if key == 'tong':
            out_str += '@ '.join(three)
            out_str += '@'
        elif key == 'tiao':
            out_str += '| '.join(three)
            out_str += '|'
        else:
            out_str += 'W '.join(three)
            out_str += 'W'
        print(out_str)

    def print_pai(self, list_pai=[]):
        if not list_pai:
            list_pai = self.list_pai
        str_pai = ''
        for one in list_pai:
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
    # client.print_pai()
    client.trible_charge()
