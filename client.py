
import copy
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

    def apply_table_seat(self):
        data = b"100\n"

        self.cli.send(data)
        recv = self.cli.recv(1024)
        str_recv = str(recv, encoding="utf8")
        print(str_recv)
        self.table_number = str_recv.split(' ')[0]
        self.table_seat_number = str_recv.split(' ')[1]

    def start(self):
        while True:
            print("+-+-+-+-+-+")
            data = b'2 1 %b %b\n' % (
                str.encode(self.table_number), str.encode(self.table_seat_number))
            self.cli.send(data)
            recv = self.cli.recv(1024)
            str_recv = str(recv, encoding="utf8")
            print(str_recv)
            if str_recv == '401':
                time.sleep(1)
            else:
                list_recv = json.loads(str_recv)
                self.list_pai = sorted(list_recv)
                break

    def choose_three_from_pai(self, pai_list):
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
            for key in range(len(hand_pai)):
                if len(hand_pai[key][1]) >= 3:
                    three = self.choose_three_from_pai(hand_pai[key][1])
                    return hand_pai[key][0], three
        else:
            pass

    def reverse_by_key(self, key, three):
        num_list = []
        if key == 'tong':
            for one in three:
                min_num = (one - 1) * 4 + 1
                max_num = one * 4
                tmp_list = copy.deepcopy(self.list_pai)
                for pai in tmp_list:
                    if pai >= min_num and pai <= max_num:
                        self.list_pai.remove(pai)
                        num_list.append(pai)
                        break
        elif key == 'tiao':
            for one in three:
                min_num = (one - 1) * 4 + 1 + 36
                max_num = one * 4 + 36
                tmp_list = copy.deepcopy(self.list_pai)
                for pai in tmp_list:
                    if pai >= min_num and pai <= max_num:
                        self.list_pai.remove(pai)
                        num_list.append(pai)
                        break
        else:
            for one in three:
                min_num = (one - 1) * 4 + 1 + 72
                max_num = one * 4 + 72
                tmp_list = copy.deepcopy(self.list_pai)
                for pai in tmp_list:
                    if pai >= min_num and pai <= max_num:
                        self.list_pai.remove(pai)
                        num_list.append(pai)
                        break

        return num_list

    def get_hand_pai_kind(self):
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
        return hand_pai

    def trible_charge(self):
        self.print_pai()
        hand_pai = self.get_hand_pai_kind()
        key, three = self.make_policy_decision('exchange', hand_pai)
        self.print_pai_by_key(key, three)
        num_list = self.reverse_by_key(key, three)

        data = b'2 2 %b %b %b %b %b\n' % (
            str.encode(self.table_number), str.encode(self.table_seat_number),
            str.encode(str(num_list[0])), str.encode(str(num_list[1])),
            str.encode(str(num_list[2]))
        )
        while True:
            self.cli.send(data)
            recv = self.cli.recv(1024)
            str_recv = str(recv, encoding="utf8")
            if str_recv == '402':
                time.sleep(1)
            else:
                num_list = str_recv.split(',')
                for one in num_list:
                    self.list_pai.append(int(one))
                self.print_pai()
                break

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
        list_pai = sorted(list_pai)
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

    def whether_seven_couple(self):
        hand_pai = self.get_hand_pai_kind()
        tong_pai = hand_pai['tong']
        tiao_pai = hand_pai['tiao']
        wan_pai = hand_pai['wan']

        tong_pai = sorted(tong_pai)
        tiao_pai = sorted(tiao_pai)
        wan_pai = sorted(wan_pai)

        for one in tong_pai:
            if tong_pai.count(one) == 2 or tong_pai.count(one) == 4:
                pass
            else:
                return False

        for one in tiao_pai:
            if tiao_pai.count(one) == 2 or tiao_pai.count(one) == 4:
                pass
            else:
                return False

        for one in wan_pai:
            if wan_pai.count(one) == 2 or wan_pai.count(one) == 4:
                pass
            else:
                return False
        return True

    def check_normal_recursion(self, pai_list, jiang_sign):
        while True:
            if not pai_list:
                return True, jiang_sign
            if jiang_sign == 1:
                one = pai_list[0]
                if pai_list.count(one) == 3:
                    count = 3
                    while count > 0:
                        pai_list.remove(one)
                        count -= 1
                    re, jiang_sign = self.check_normal_recursion(pai_list, jiang_sign)
                    return re, jiang_sign
                elif one + 1 in pai_list and one + 2 in pai_list:
                    pai_list.remove(one)
                    pai_list.remove(one + 1)
                    pai_list.remove(one + 2)
                    re, jiang_sign = self.check_normal_recursion(pai_list, jiang_sign)
                    return re, jiang_sign
                else:
                    return False, jiang_sign

            else:
                for one in pai_list:
                    if pai_list.count(one) > 1:
                        pai_list.remove(one)
                        pai_list.remove(one)
                        re, jiang_sign = self.check_normal_recursion(pai_list, 1)
                        return re, jiang_sign
                    else:
                        pass
                return False, jiang_sign

    def whether_normal(self):
        hand_pai = self.get_hand_pai_kind()
        tong_pai = hand_pai['tong']
        tiao_pai = hand_pai['tiao']
        wan_pai = hand_pai['wan']

        tong_pai = sorted(tong_pai)
        tiao_pai = sorted(tiao_pai)
        wan_pai = sorted(wan_pai)

        jiang_sign = 0
        re, jiang_sign = self.check_normal_recursion(tong_pai, jiang_sign)
        if not re:
            return False
        re, jiang_sign = self.check_normal_recursion(tiao_pai, jiang_sign)
        if not re:
            return False
        re, jiang_sign = self.check_normal_recursion(wan_pai, jiang_sign)
        if not re:
            return False
        return True

    def whether_win(self):
        re = self.whether_seven_couple()
        if re:
            return True
        re = self.whether_normal()
        if re:
            return True
        return False

    def choose_from_pai(self):
        lenth = len(self.list_pai)
        rd = random.randint(1, lenth)
        temp = self.list_pai[rd - 1]
        self.list_pai.remove(temp)
        return temp

    def discard(self):
        re = self.whether_win()
        if re:
            return True, 0
        else:
            re = self.choose_from_pai()
            return False, re

    def play(self):
        while True:
            if len(self.list_pai) % 3 == 2:
                re, pai = self.discard()
                if re:
                    data = b'2 3 %b %b\n' % (
                        str.encode(self.table_number), str.encode(self.table_seat_number))
                    self.cli.send(data)
                    recv = self.cli.recv(1024)
                    str_recv = str(recv, encoding="utf8")
                    if str_recv == '200':
                        break
                else:
                    data = b'2 4 %b %b %s\n' % (
                        str.encode(self.table_number), str.encode(self.table_seat_number),
                        str.encode(str(pai))
                    )
                    self.cli.send(data)
                    recv = self.cli.recv(1024)
                    str_recv = str(recv, encoding="utf8")
            else:
                data = b'2 5 %b %b\n' % (
                    str.encode(self.table_number), str.encode(self.table_seat_number)
                )
                self.cli.send(data)
                recv = self.cli.recv(1024)
                str_recv = str(recv, encoding="utf8")
                if str_recv == '202':
                    time.sleep(1)
                elif str_recv == '203':
                    break
                else:
                    print(str_recv)


if __name__ == '__main__':
    client = Client()
    client.apply_table_seat()
    client.start()
    client.trible_charge()
    client.play()
