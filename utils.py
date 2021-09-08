def flatten(something):
    """ Flattens a multidimensional array. """
    if isinstance(something, (list, tuple, set, range)):
        for sub in something:
            yield from flatten(sub)
    else:
        yield something


def get_available(existing_bookings):
    """ Search the array of cells and return all that are unbooked. """
    available = []

    for cell in existing_bookings:
        if (cell.group_name is None) and (cell not in available):
            available.append(cell)

    return available

def sort_by_prefrence(bookings):
    """
    Sort rooms by their 'quality' field. This function is pretty simple but can
    be expaded in the future for more advanced room sorting (if you ever want it...)
    """
    return sorted(bookings, key=lambda x: x.room_meta.quality, reverse=True)

def get_within_times(bookings, start=0, end=0):
    """
    Return bookings that are within the given times.

    eg. Between 12600 and 18000 would include 12600 <= x < 18000.
    """
    return list(filter(lambda x: x.is_between_times(start, end), bookings))


def get_unbooked(bookings):
    """ Filter all rooms already booked. """
    return list(filter(lambda x: not x.is_booked(), bookings))


def get_our_bookings(existing_bookings, possible_names):
    """
    Search the array of cells and return all that are booked by us

    TODO: Other groups that happen to use the same name
    as us will be matched here. Not sure how to address this yet
    """
    ours = []

    for cell in existing_bookings:
        if cell.group_name in possible_names:
            ours.append(cell)

    return ours


def to_uvic_url(day, month, year, area):
    """ Turns the {day, month, year, area} into a url. """
    complete_url = f"https://webapp.library.uvic.ca/studyrooms/index.php?view=day&day={day}&month={month}&year={year}&area={area}"
    return complete_url