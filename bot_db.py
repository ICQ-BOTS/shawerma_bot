import tarantool
from openpyxl import Workbook

# --------------------------------connection management-------------------


def connect(db_host, db_port):
    global statistics, connection
    connection = tarantool.connect(db_host, db_port)
    statistics = connection.space("statistics")


def disconnect():
    global connection
    connection.close()


# ----------------------------------------data----------------------------------------


def load_admins(loaded_array):
    global admins
    admins = loaded_array


def init_user_info(user):
    global admins
    if user.id in admins:
        user.permissions = 2
    else:
        user.permissions = 0
    user.last_message_id = None
    user.state_params = {}


def add_user_picture_gen(user_id):
    global statistics
    statistics.upsert((user_id, 1), [("+", 1, 1)])


class TestStatisticsObject:
    def __init__(self, sheet):
        self.sheet = sheet
        self.sheet["A1"] = "UIN"
        self.sheet["B1"] = "Кол-во"
        self.sheet.column_dimensions["A"].width = 25
        self.sheet.column_dimensions["B"].width = 25
        self.current_row = 3
        self.all_count = 0
        self.rows_count = 0

    def add(self, user_id, count):
        self.sheet["A%d" % (self.current_row)] = user_id
        self.sheet["B%d" % (self.current_row)] = count
        self.current_row += 1
        self.all_count += count
        self.rows_count += 1

    def end(self):
        self.sheet["A2"] = self.rows_count
        self.sheet["B2"] = self.all_count


def get_statistics():
    global statistics
    wb = Workbook()
    wb.remove(wb.active)

    # create worksheets
    common_statistics = TestStatisticsObject(wb.create_sheet("Статистика", 0))

    for row in statistics.select():
        user_id = row[0]
        count = row[1]
        common_statistics.add(user_id, count)

    common_statistics.end()
    return wb


def get_fast_statistics():
    global statistics

    common_statistics = 0
    users_count = 0

    for row in statistics.select():
        count = row[1]

        common_statistics += count
        users_count += 1

    return common_statistics, users_count
