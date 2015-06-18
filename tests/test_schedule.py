#!/usr/bin/env python
# coding=utf-8
import calendar
import operator as op
import random as rnd
import datetime as dt
from itertools import islice

import pytest
from dateutil.relativedelta import relativedelta
from funclib.positional import first
from six.moves import range

from tempo.schedule import Schedule
from tests.utils import schedule_kwargs


@pytest.mark.parametrize('kwargs, datetime, expected', [
    # There was a bug when first result was with 20 hour
    # because of wrong calculation of a first date in a sequence.
    ({'years': [2000], 'months': [3], 'hours': [0, 20]},
     dt.datetime(2000, 1, 1, 5, 0, 0), [
        dt.datetime(2000, 3, 1, 0, 0, 0),
        dt.datetime(2000, 3, 1, 0, 0, 1),
        dt.datetime(2000, 3, 1, 0, 0, 2)
    ]),
])
def test_forward(kwargs, datetime, expected):
    """Corner cases of `Schedule.forward`."""
    schedule = Schedule(**kwargs)
    actual = list(islice(schedule.forward(datetime), len(expected)))
    assert actual == expected


def forward(datetime, seconds_of_the_day=None, seconds=None, minutes=None,
            hours=None, days=None, weekdays=None, months=None, years=None):
    """'Brute force' implementation of `Schedule.forward` functionality."""
    delta = dt.timedelta(seconds=1)

    seconds_of_the_day = set(seconds_of_the_day or Schedule.SECONDS_OF_THE_DAY)
    seconds = set(seconds or Schedule.SECONDS)
    minutes = set(minutes or Schedule.MINUTES)
    hours = set(hours or Schedule.HOURS)
    days = set(days or Schedule.DAYS)
    weekdays = set(weekdays or Schedule.WEEKDAYS)
    months = set(months or Schedule.MONTHS)
    years = set(years or Schedule.YEARS)

    years_sorted = sorted(years)
    seconds_of_the_day_check = lambda d: (d.hour * 60 * 60 + d.minute * 60 +
                                          d.second) in seconds_of_the_day
    checks = [
        [(lambda d: d.second in seconds), seconds_of_the_day_check],
        [(lambda d: d.minute in minutes), seconds_of_the_day_check],
        [(lambda d: d.hour in hours), seconds_of_the_day_check],
        [(lambda d: d.day in days), lambda d: d.weekday() in weekdays],
        [lambda d: d.month in months],
        [lambda d: d.year in years]
    ]

    def find_closest_year(datetime):
        return datetime.replace(
            year=first((y for y in years_sorted if y >= datetime.year)),
            month=min(months), day=1, hour=0, minute=0, second=0
        ).replace(microsecond=0)

    try:
        datetime = find_closest_year(datetime)
    except IndexError:
        raise StopIteration

    calendar_cofigurations_traversed = set()
    yields = 0

    max_year = max(years)

    while True:
        initial_year = datetime.year
        for check_list in checks:
            if not any(check(datetime) for check in check_list):
                break
        else:
            yield datetime
            yields += 1

        try:
            datetime += delta
        except OverflowError:
            break

        if datetime.year not in years:
            try:
                datetime = find_closest_year(datetime)
            except IndexError:
                raise StopIteration

        if datetime.month not in months:
            datetime += relativedelta(months=1, day=1, hour=0,
                                      minute=0, second=0)

        if datetime.day not in days and datetime.weekday() not in weekdays:
            datetime += relativedelta(days=1, hour=0, minute=0, second=0)

        if datetime.year > max_year:
            break

        if initial_year != datetime.year and initial_year in years:
            calendar_cofigurations_traversed.add(
                (dt.datetime(initial_year, 1, 1).weekday(),
                 calendar.isleap(initial_year))
            )
            if len(calendar_cofigurations_traversed) == 14 and yields == 0:
                # Traversed all possible calendars with no results - breaking.
                raise StopIteration


def test_forward_random():
    """Random comparisons between 'brute force' calculated sequences
    and `Schedule.forward` outputs."""
    for i in range(10):
        kwargs = schedule_kwargs()

        datetime = dt.datetime(min(kwargs['years']), 1, 1)
        delta = datetime - dt.datetime.min

        datetime = datetime - relativedelta(
            seconds=rnd.randint(0, delta.total_seconds())
        )
        actual = list(islice(Schedule(**kwargs).forward(datetime), 10))
        expected = list(islice(forward(datetime, **kwargs), 10))

        assert actual == expected
