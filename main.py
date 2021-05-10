import os.path
import time
import random
try:
    import requests as req
except ModuleNotFoundError:
    print('Install requests lib using "pip install requests" or "pip3 install requests".')

import os
if not os.path.isfile('settings.py'):
    with open('settings.py', 'w') as f:
        template = ['service_token = ',
                    'user_token = ',
                    'group_id = ',
                    'group_token = ']
        for template_line in template:
            f.write(template_line + '"' + input(template_line) + '"' + '\n')
        f.write('api_version = "5.130"')
        f.write('mode2path = {"b": "black_group_list.txt",\n' +
                '             "s": "short_group_list.txt",\n' +
                '             "f": "full_group_list.txt"}\n')

if os.path.isfile('settings.py'):
    import settings


def create_file(path):
    if not os.path.isfile(path):
        with open(path, 'w') as file:
            file.write('')


create_file('black_group_list.txt')
create_file('short_group_list.txt')
create_file('full_group_list.txt')


class DataBase:

    def __init__(self, file):
        self.filename = file
        database = open(self.filename, 'r')
        self.data = [line[:-1] for line in database]
        database.close()

    def print_line(self, line_number):
        string = self.data[line_number - 1]
        print(string)

    def print_all_lines(self):
        for line in self.data:
            print(line)

    def add_line(self, line):
        self.data.append(line)

    def add_lines(self, lines):
        for line in lines:
            self.add_line(line)

    def remove_line(self, line):
        self.data.remove(line)

    def sort_database(self):
        self.data.sort()

    def remove_equals_and_sort(self):
        data_set = {i for i in self.data}
        self.data = sorted(data_set)

    def save_database_changes(self):
        with open(self.filename, 'w') as database:
            for line in self.data:
                database.write(line + '\n')


def update_base(path, lines):
    base = DataBase(path)
    base.add_lines(lines)
    base.remove_equals_and_sort()
    base.save_database_changes()


def remove_line(path, line):
    base = DataBase(path)
    base.remove_line(line)
    base.save_database_changes()


class ApiManager:

    def __init__(self):
        self.service_token = settings.service_token
        self.user_token = settings.user_token
        self.group_id = settings.group_id
        self.group_token = settings.group_token
        self.api_version = settings.api_version

    def api(self, method, parameters, token):
        parameters = '&'.join([f'{parameter}={parameters[parameter]}' for parameter in parameters])
        while True:
            try:
                resp = req.get(f'https://api.vk.com/method/{method}?'
                               f'{parameters}&'
                               f'access_token={token}&'
                               f'v={self.api_version}')
                try:
                    if 'error' in resp.json() and resp.json()['error']['error_code'] == 6:
                        pass
                    else:
                        break
                except Exception as ex:
                    print('Json error?', ex)
                    # print(resp)
                    # print(parameters, '\n\n')
                    break
            except Exception as ex:
                time.sleep(3)
                print('ConnectionError?', ex)
                # if ex == 'Expecting value: line 1 column 1 (char 0)':
                #     print(resp)
        return resp

    def get_user_id(self, user_url):       # get user_url return user_id
        if user_url.startswith('https://'):
            user_url = user_url[8:]
        if user_url.startswith('vk.com/'):
            user_url = user_url[7:]

        resp = self.api('users.get',
                        {'user_ids': user_url},
                        self.service_token).json()
        if 'error' in resp:
            return 'error'
        user_id = resp['response'][0]['id']
        return user_id

    def get_group_id_and_name(self, group_url):
        if group_url.startswith('https://'):
            group_url = group_url[8:]
        if group_url.startswith('vk.com/'):
            group_url = group_url[7:]

        resp = self.api('groups.getById',
                        {'group_id': group_url},
                        self.service_token).json()
        group_id = resp['response'][0]['id']
        group_name = resp['response'][0]['name']
        return group_id, group_name

    def extract_user_groups(self, user_id):
        resp = self.api('groups.get',
                        {'user_id': user_id, 'extended': '1'},
                        self.user_token).json()
        return resp

    def execute(self, code):
        resp = self.api('execute',
                        {'code': code},
                        self.group_token).json()
        return resp

    def get_long_poll_server(self):
        group_id = self.get_group_id_and_name(self.group_id)[0]
        resp = self.api('groups.getLongPollServer',
                        {'group_id': group_id},
                        self.group_token).json()
        return resp

    def message(self, target_user_id, message):
        resp = self.api('messages.send',
                        {'user_id': target_user_id, 'random_id': random.randint(1, 1000000), 'message': message},
                        self.group_token).json()
        return resp

    def save_page(self, message, title):
        resp = self.api('pages.save',
                        {'text': message, 'group_id': self.group_id, 'title': title},
                        self.user_token).json()
        page_id = resp['response']
        return page_id


class CheckVkGroups:

    def __init__(self):
        self.api = ApiManager()

    def add_line(self, path, group_url):
        group_id, group_name = self.api.get_group_id_and_name(group_url)
        update_base(path, [f'{group_id}::{group_name}'])

    def extract_user_groups(self, user_id,
                            path='full_group_list.txt',
                            blacklist_path='black_group_list.txt'):
        black_list = DataBase(blacklist_path).data
        resp = self.api.extract_user_groups(user_id)
        lines = [f'{group["id"]}::{group["name"]}' for group in resp['response']['items']
                 if f'{group["id"]}::{group["name"]}' not in black_list]
        update_base(path, lines)

    @staticmethod
    def code_assembler(data_slice, user_id):
        id_list = [line.split('::')[0] for line in data_slice]
        id_list = '", "'.join(id_list)
        code_0 = f'var a = (["{id_list}"]);'
        code_1 = """
        var b = ([]);
        var i = 0;
        while (i < """
        code_2 = """) {
            b.push(API.groups.isMember({"group_id": a[i], "user_id": """
        code_3 = """}));
            i = i - -1;
        }
        return b;"""
        code = code_0 + code_1 + f'{len(data_slice)}' + code_2 + str(user_id) + code_3
        return code

    def check_groups(self, user_id, path, blacklist_path='black_group_list.txt'):
        data = DataBase(path).data
        error_to_delete = ['Access to group denied: access to the group members is denied',
                           'Access denied: no access to this group']    # ошибки, которые ведут к удалению из списка
        groups = []
        slice_quantity = len(data) // 25            # т. к. в execute выполняется максимум 25 запросов api
        for slice_number in range(slice_quantity + 1):
            if slice_number < slice_quantity:       # если номер среза меньше количества полных срезов, то есть 25 строк
                data_slice = data[slice_number * 25:(slice_number + 1) * 25]
            elif slice_number == slice_quantity:    # последний срез, оставшиеся строки
                data_slice = data[slice_quantity * 25:]
            else:
                return 'error'

            code = self.code_assembler(data_slice, user_id)     # сборка кода для api
            resp = self.api.execute(code)

            if 'error' in resp:
                print('error', resp)
                continue
            elif 'execute_errors' in resp and resp['execute_errors'][0]['error_msg'] in error_to_delete:
                resp_str = [str(i) for i in resp['response']]
                for i in range(resp_str.count('False')):        # обработка каждой ошибки на удаление
                    error_id = resp_str.index('False')          # нахождение индекса строки
                    line = data_slice[error_id]
                    print(f'Delete: \n{line}\n')                # вывод
                    update_base(blacklist_path, [line])         # запоминание
                    remove_line(path, line)                     # удаление из списка-файла
                    data_slice.remove(line)                     # удаление из списка-среза
                    resp_str.remove('False')                    # удаление из списка-ответа
                resp['response'] = [int(i) for i in resp_str]   # возвращение списка в начальный вид без False
            # print(resp)
            answers = resp['response']                          # извлечение списка ответов из json
            for i in range(len(answers)):
                if answers[i]:
                    groups.append(data_slice[i])
                    # line = data_slice[i].split('::')
                    # print(f'{line[1]}\nhttps://vk.com/public{line[0]}\n')
        return groups


class UserInterface:

    def __init__(self):
        self.api = ApiManager()
        self.checker = CheckVkGroups()
        self.mode2path = settings.mode2path

        resp = self.api.get_long_poll_server()
        # здесь должна быть проверка ответа на ошибки
        self.key = resp['response']['key']
        self.server = resp['response']['server']
        self.ts1 = resp['response']['ts']

    def print(self, message, target_user_id):
        resp = self.api.message(target_user_id, message)
        print(resp)

    @staticmethod
    def response_assembler(groups):
        message = ''
        for group in groups:
            message += f'https://vk.com/public{group.split("::")[0]}\n'
        message += str(len(groups))
        return message.replace('&', '*a*').replace('#', '*ht*')

    def check_user_groups(self, full_command, target):
        if len(full_command) == 3:
            mode = full_command[1]
            user_url = full_command[2]

            user_id = self.api.get_user_id(user_url)             # получение user_id из url
            if user_id == 'error':
                self.print('Invalid user url', target)
            else:
                self.print(user_id, target)

                if mode in self.mode2path:
                    groups = self.checker.check_groups(user_id, self.mode2path[mode])   # нахождение групп
                    message = self.response_assembler(groups)                 # сбор текста для wiki-страницы
                    page_id = self.api.save_page(message, user_id)            # создание wiki-страницы и получение ее id
                    page_url = f'https://vk.com/page-201873635_{page_id}'     # сбор ссылки с помощью id wiki-страницы
                    self.print(page_url,  target)                             # отправка ссылки сообщением
                else:
                    self.print('Unknown mode', target)
        else:
            self.print('Invalid command: expected 3 command sections.', target)
        self.print('.', target)

    def add_groups_to_list(self, full_command, target):
        if len(full_command) == 2:
            mode = full_command[1]
            # url_amount = int(input('Amount: '))
            self.print('Enter groups url (until "end"): ', target)

            if mode in self.mode2path:
                data_path = self.mode2path[mode]

                url = input()
                while url != 'end':
                    self.checker.add_line(data_path, url)
                    url = input()
            else:
                self.print('Unknown mode', target)
        else:
            self.print('Invalid command: expected 2 command sections.', target)
        self.print('.', target)

    def extract_user_groups_to_list(self, full_command, target):
        if len(full_command) == 3:
            mode = full_command[1]
            user_url = full_command[2]
            user_id = self.api.get_user_id(user_url)
            if user_id == 'error':
                self.print('Extraction failed: error with user_id', target)
            else:
                if mode in self.mode2path:
                    self.checker.extract_user_groups(user_id, self.mode2path[mode])
                else:
                    self.print('Unknown mode', target)
        else:
            self.print('Invalid command: expected 3 command sections.', target)
        self.print('.', target)

    def print_documentation(self, full_command, target):
        if len(full_command) == 1:                         # просто заглушка
            pass
        documentation = DataBase('documentation.txt')
        documentation.print_all_lines()
        self.print('.', target)

    def main(self):
        commands = {'check': self.check_user_groups,
                    # 'add': self.add_groups_to_list,
                    'extract': self.extract_user_groups_to_list,
                    # 'help': self.print_documentation
                    }
        ts = self.ts1
        while True:
            while True:
                resp = req.get(f'{self.server}?act=a_check&key={self.key}&ts={ts}&wait=25').json()
                print(resp)
                if len(resp['updates']) > 0:
                    event = resp['updates'][0]['object']
                    target = event['user_id']
                    full_command = event['body'].split()
                    ts = resp['ts']
                    break
            command = full_command[0]

            if command in commands:
                commands[command](full_command, target)
            else:
                self.print('Unknown command. To see a list of commands type "help".', target)


def main():
    ui = UserInterface()
    ui.main()


if __name__ == '__main__':
    main()

"""
ToDo:


Многопоточный вызов execute-запросов

Вынести CallBack-систему в отдельный класс

BugRep: при изменении группой названия, 
    это принимается программой за новую группу,
    что приводит к дублированию в базе.
Fix1: использование нормальной СУБД
Fix2: переход с формата 'id::name' на формат 'id', для уникализации строк

Сделать прогресс бар

"""
