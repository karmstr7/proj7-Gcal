import arrow
from datetime import datetime


class AvailableDatetime:
    def __init__(self, begin_datetime, end_datetime):
        self.begin_datetime = begin_datetime
        self.end_datetime = end_datetime

        self.begin_date = self.__iso_to_date(begin_datetime)
        self.end_date = self.__iso_to_date(end_datetime)

        self.begin_time = self.__iso_to_time(begin_datetime)
        self.end_time = self.__iso_to_time(end_datetime)
        self.available_times = []

    @staticmethod
    def __iso_to_date(iso_str):
        get_arrow = arrow.get(iso_str).format('YYYY-MM-DD')
        get_datetime_date = datetime.strptime(get_arrow, "%Y-%m-%d").date()
        return get_datetime_date

    @staticmethod
    def __iso_to_time(iso_str):
        get_arrow = arrow.get(iso_str).format('HH:mm')
        get_datetime_date = datetime.strptime(get_arrow, "%H:%M").time()
        return get_datetime_date

    def get_begin_date(self):
        return self.begin_date

    def get_begin_time(self):
        return self.begin_time

    def get_end_date(self):
        return self.end_date

    def get_end_time(self):
        return self.end_time

    def check_busy(self, event_start, event_end):
        event_start_date = self.__iso_to_date(event_start)
        event_end_date = self.__iso_to_date(event_end)
        event_start_time = self.__iso_to_time(event_start)
        event_end_time = self.__iso_to_time(event_end)

        if self.begin_date <= event_end_date <= self.end_date:
            if self.begin_time < event_end_time <= self.end_time:
                return True


def get_busy_events(events, begin_datetime, end_datetime):
    ad = AvailableDatetime(begin_datetime, end_datetime)
    busy_list = []
    for event in events:
        try:
            if ad.check_busy(event[2]['start']['dateTime'], event[3]['end']['dateTime']):
                busy_list.append([event[0]['calendar'],
                                  event[1]['summary'],
                                  event[2]['start']['dateTime'],
                                  event[3]['end']['dateTime']])
        except KeyError:
            continue
    return busy_list
