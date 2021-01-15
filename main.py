import os.path
import time
try:
    import requests as req
except ModuleNotFoundError:
    print('Install requests lib using "pip install requests"')

if not os.path.isfile('settings.txt'):
    with open('settings.txt', 'w') as f:
        f.write(input('Service token:\n') + '\n')
        f.write(input('User token:\n') + '\n')
        f.write(input('Group token:\n') + '\n')
        f.write(input('Api version:\n') + '\n')


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


class CheckVkGroups:

    def __init__(self):
        settings = DataBase('settings.txt').data
        self.service_token = settings[0]
        self.user_token = settings[1]
        self.group_token = settings[2]
        self.api_version = settings[3]

    @staticmethod
    def print_group(line):
        line = line.split('::')
        group_id = line[0]
        group_name = line[1]
        print(f'{group_name}\nhttps://vk.com/public{group_id}\n')

    def api(self, method, parameters, token):
        parameters = '&'.join([f'{parameter}={parameters[parameter]}' for parameter in parameters])
        while True:
            try:
                resp = req.get(f'https://api.vk.com/method/{method}?'
                               f'{parameters}&'
                               f'access_token={token}&'
                               f'v={self.api_version}')
                break
            except Exception as ex:
                time.sleep(1)
                print('ConnectionError?', ex)
        if 'error' in resp.json():
            print(f'Error in api:\n{resp.json()["error"]["error_msg"]}')
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
            print(f'Error in user_id:\n{resp}')
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

    def add_line(self, path, group_url):
        group_id, group_name = self.get_group_id_and_name(group_url)
        update_base(path, [f'{group_id}::{group_name}'])

    def extract_user_groups(self, user_id,
                            path='full_group_list.txt',
                            blacklist_path='black_group_list.txt'):
        black_list = DataBase(blacklist_path).data
        resp = self.api('groups.get',
                        {'user_id': user_id, 'extended': '1'},
                        self.user_token).json()
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
                           'Access denied: no access to this group']
        counter = 0
        slice_quantity = len(data) // 25            # т. к. в execute выполняется максимум 25 запросов api
        for slice_number in range(slice_quantity + 1):
            if slice_number < slice_quantity:       # если номер среза меньше количества полных срезов, то есть 25 строк
                data_slice = data[slice_number * 25:(slice_number + 1) * 25]
            elif slice_number == slice_quantity:    # последний срез, оставшиеся строки
                data_slice = data[slice_quantity * 25:]
            else:
                return 'error'

            code = self.code_assembler(data_slice, user_id)     # сборка кода для api
            resp = self.api('execute',
                            {'code': code},
                            self.group_token).json()

            if 'error' in resp:
                print('error', resp)
            elif ('execute_errors' in resp) and (resp['execute_errors'][0]['error_msg'] in error_to_delete):
                line = data_slice[[str(i) for i in resp['response']].index('False')]  # перевод в строку для нахождения
                print(f'Delete error: \n{line}\n')          # вывод
                update_base(blacklist_path, [line])     # запоминание
                remove_line(path, line)                 # удаление
            else:
                # print(resp)
                answers = resp['response']      # извлечение списка ответов из json
                for i in range(len(answers)):
                    if answers[i]:
                        counter += 1
                        line = data_slice[i].split('::')
                        print(f'{line[1]}\nhttps://vk.com/public{line[0]}\n')
            time.sleep(0.051)                    # метод execute может выполняться только 20 раз в секунду (для групп)
        print(counter)


class UserInterface:

    def __init__(self):
        self.checker = CheckVkGroups()
        self.mode2path = {'s': 'short_group_list.txt',
                          'f': 'full_group_list.txt'}

    def check_user_groups(self, full_command):
        if len(full_command) == 3:
            mode = full_command[1]
            user_url = full_command[2]

            user_id = self.checker.get_user_id(user_url)             # получение user_id из url
            if user_id == 'error':
                print('Invalid user url')
            else:
                print()

                if mode in self.mode2path:
                    self.checker.check_groups(user_id, self.mode2path[mode])
                else:
                    print('Unknown mode')
        else:
            print('Invalid command: expected 3 command sections.')
        print('.')

    def add_groups_to_list(self, full_command):
        if len(full_command) == 2:
            mode = full_command[1]
            # url_amount = int(input('Amount: '))
            print('Enter groups url (until "end"): ')

            if mode in self.mode2path:
                data_path = self.mode2path[mode]

                url = input()
                while url != 'end':
                    self.checker.add_line(data_path, url)
                    url = input()
            else:
                print('Unknown mode')
        else:
            print('Invalid command: expected 2 command sections.')
        print('.')

    def extract_user_groups_to_list(self, full_command):
        if len(full_command) == 3:
            mode = full_command[1]
            user_url = full_command[2]
            user_id = self.checker.get_user_id(user_url)
            if user_id == 'error':
                print('Extraction failed: error with user_id')
            else:
                if mode in self.mode2path:
                    self.checker.extract_user_groups(user_id, self.mode2path[mode])
                else:
                    print('Unknown mode')
        else:
            print('Invalid command: expected 3 command sections.')
        print('.')

    @staticmethod
    def print_documentation(full_command):
        if len(full_command) == 1:                         # просто заглушка
            pass
        documentation = DataBase('documentation.txt')
        documentation.print_all_lines()
        print('.')

    def main(self):
        commands = {'check': self.check_user_groups,
                    'add': self.add_groups_to_list,
                    'extract': self.extract_user_groups_to_list,
                    'help': self.print_documentation}
        while True:
            full_command = input().split()
            command = full_command[0]

            if command in commands:
                commands[command](full_command)
            else:
                print('Unknown command. To see a list of commands type "help".')


def main():
    ui = UserInterface()
    ui.main()


if __name__ == '__main__':
    main()

"""
ToDo:


Добавить возможность добавления пользовательских модов через настройки

Убрать волочение перехваченных ошибок через несколько функций

Нормальная обработка исключений

В check_group сделать аккумулирование групп и возврат их в UI

Перенести print в UI

Сделать функцию очистки списка от мелких групп

Сделать доступ к программе через бота

Сделать прогресс бар


"""
