import datetime

class ExecutionSchedule:

    def __init__(self):
        pass

class Market(ExecutionSchedule):
    pass

class Limit(ExecutionSchedule):
    pass

class GoodTillCanceled(Limit):
    pass

class GoodForDay(Limit):
    pass

class GoodTillDate(Limit):

    def __init__(self, date: datetime.date):
        super().__init__()
        self.date = date

class ImmediateOrCancel(Limit):
    pass