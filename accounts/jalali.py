"""The Persian calendar, for the one date in the product that a learner reads.

``UserProfile.target_date`` is stored as an ordinary ``DateField``, and everything that
counts with it — the weeks left, the pace, the "passed" state — stays in Gregorian days,
because that is what a date library can count. What a Persian speaker *reads* is a Jalali
date, and what they should be able to *choose* is one too: the browser's own date picker
speaks the browser's locale, so a learner in Iran was being asked to pick a day in a
calendar they do not use.

So this module is the only place that converts, in both directions, and both the form and
the templates go through it:

* ``to_gregorian`` turns the three menus into the date the model stores,
* ``from_gregorian`` turns the stored date back into those menus when the page is reopened,
* ``format_date`` writes it the way it is read, and ``days_in_month`` is what keeps the
  day menu honest.

The arithmetic is the standard Jalali conversion — a 33-year cycle of leap years — rather
than a table of dates, so it keeps working for every year the menus offer without anyone
having to extend a list. It is also what ``to_gregorian``/``from_gregorian`` are checked
against in the tests: a round trip must return the date it started with.

Nothing here reads the database or knows about Django; it works on ``datetime.date``.
"""

from datetime import date

#: The Jalali month names, in calendar order. Month 1 is ``MONTHS[0]``.
MONTHS = (
    "فروردین",
    "اردیبهشت",
    "خرداد",
    "تیر",
    "مرداد",
    "شهریور",
    "مهر",
    "آبان",
    "آذر",
    "دی",
    "بهمن",
    "اسفند",
)

#: How many Jalali years ahead the year menu offers. A learner preparing for an Ausbildung
#: picks a date within a year or two; four is already generous, and keeping the menu short
#: keeps it usable on a phone.
YEARS_AHEAD = 4

#: Persian digits, so a date is written in the numerals the page is written in. The menus
#: submit Latin digits — those are what the server parses — and only the display is Persian.
PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹"


def to_gregorian(year, month, day):
    """The Gregorian ``date`` for a Jalali year, month and day.

    The caller has already checked that the day fits the month
    (``days_in_month``); this function assumes a real Jalali date.
    """
    # A Gregorian year is the Jalali year plus 621, and the two calendars differ by the
    # days this offset represents. Counting days from an epoch and then splitting them
    # into Gregorian years/months is exact, and avoids any month-by-month bookkeeping.
    jalali_year = year + 1595
    days = -355668 + (365 * jalali_year) + ((jalali_year // 33) * 8) + (((jalali_year % 33) + 3) // 4) + day

    if month < 7:
        days += (month - 1) * 31
    else:
        days += ((month - 7) * 30) + 186

    gregorian_year = 400 * (days // 146097)
    days = days % 146097

    if days > 36524:
        days -= 1
        gregorian_year += 100 * (days // 36524)
        days = days % 36524
        if days >= 365:
            days += 1

    gregorian_year += 4 * (days // 1461)
    days = days % 1461

    if days > 365:
        gregorian_year += (days - 1) // 365
        days = (days - 1) % 365

    gregorian_day = days + 1

    month_lengths = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

    if (gregorian_year % 4 == 0 and gregorian_year % 100 != 0) or gregorian_year % 400 == 0:
        month_lengths[2] = 29

    gregorian_month = 0
    while gregorian_month < 13 and gregorian_day > month_lengths[gregorian_month]:
        gregorian_day -= month_lengths[gregorian_month]
        gregorian_month += 1

    return date(gregorian_year, gregorian_month, gregorian_day)


def from_gregorian(value):
    """The Jalali ``(year, month, day)`` for a Gregorian ``date``.

    A Jalali year is the Gregorian year minus 621 and begins in March, so only the days
    before that year's Nowruz belong to the previous Jalali year. Rather than restate that
    boundary, this asks ``to_gregorian`` when this year's Nowruz fell — the two directions
    then agree by construction, which is what the round-trip test checks.
    """
    year = value.year - 621

    if value < to_gregorian(year, 1, 1):
        year -= 1

    # Then the months, from the new year, using the same month lengths the day menu uses.
    days = (value - to_gregorian(year, 1, 1)).days
    month = 1

    while month <= 12:
        length = days_in_month(year, month)

        if days < length:
            break

        days -= length
        month += 1

    return year, month, days + 1


def is_leap_year(year):
    """Whether a Jalali year has 366 days.

    Asked as "is the next new year one day further away?": the leap rule is stated in the
    way the calendar is defined rather than restated as a cycle formula, and it is checked
    with ``to_gregorian`` alone — ``from_gregorian`` needs the month lengths, so a leap test
    that went through it would call itself.
    """
    return (to_gregorian(year + 1, 1, 1) - to_gregorian(year, 1, 1)).days == 366


def days_in_month(year, month):
    """How many days a Jalali month has.

    The first six months have 31 days, the next five have 30, and Esfand has 29, or 30 in
    a leap year.
    """
    if month <= 6:
        return 31

    if month <= 11:
        return 30

    if is_leap_year(year):
        return 30

    return 29


def year_choices(today):
    """The years the year menu offers, oldest last: this year and the next few."""
    today_year, _, _ = from_gregorian(today)

    years = []
    for offset in range(YEARS_AHEAD + 1):
        years.append(today_year + offset)

    return years


def persian_number(value):
    """``value`` written with Persian digits, for the labels the page shows.

    The menus *submit* Latin digits — those are what the server parses — so only the label
    is translated. The same helper is what ``format_date`` writes its numbers with.
    """
    translated = []

    for character in str(value):
        if character.isdigit():
            translated.append(PERSIAN_DIGITS[int(character)])
        else:
            translated.append(character)

    return "".join(translated)


def format_date(value):
    """A Gregorian ``date`` written as a Jalali date, in Persian digits.

    ``۲۶ آذر ۱۴۰۵`` — the month's name, not its number, because that is how a date is read
    aloud and how a learner checks it against a calendar.
    """
    year, month, day = from_gregorian(value)

    return persian_number(f"{day} {MONTHS[month - 1]} {year}")
