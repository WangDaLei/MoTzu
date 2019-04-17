
import json
import time
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
