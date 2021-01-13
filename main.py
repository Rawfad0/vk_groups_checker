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

    def __init__(self, service_token, user_token, api_version):
        self.service_token = service_token
        self.user_token = user_token
        self.api_version = api_version

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

    # Возвращает информацию о том, является ли пользователь участником сообщества.
    def check_group(self, group_id, user_id):
        resp = self.api('groups.isMember',
                        {'group_id': group_id, 'user_id': user_id},
                        self.service_token).json()

        return resp

    def check_groups(self, user_id, path, blacklist_path='black_group_list.txt'):
        data = DataBase(path).data
        error_to_delete = ['Access to group denied: access to the group members is denied',
                           'Access denied: no access to this group']
        count = 0                                           # счетчик соответствующих групп
        for line in data:
            group_id = line.split('::')[0]
            resp = self.check_group(group_id, user_id)
            if 'error' in resp:
                if resp['error']['error_msg'] in error_to_delete:
                    update_base(blacklist_path, [line])     # запоминание проблемной группы, не будет добавлена повторно
                    remove_line(path, line)
                    print(f'Deleted: {line}\n')
            elif resp['response']:
                count += 1
                self.print_group(line)
        print(count)


class UserInterface:

    def __init__(self):
        settings = DataBase('settings.txt').data
        service_token = settings[0]
        user_token = settings[1]
        api_version = settings[2]

        self.checker = CheckVkGroups(service_token, user_token, api_version)

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


"""
