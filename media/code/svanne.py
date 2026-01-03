from datetime import datetime
import argparse

def get_svanne(incept, print_gregorian=False, print_svanne=False, user_date=None):
    """
    Uses a numeric to alphabetic dictionary as well as the built-in
    python datetime library to construct the current Svannic date.
    This script properly handles leap years.

    Inputs:

    incept          - the repository inception date.
    print_gregorian - prints the current gregorian date (default: False)
    print_svanne   - prints the current svannic date (default: False)
    user_date       - if provided, overrides datetime.now() with proposed date (dd-mm-yyyy)

    Outputs:

    svanne - svanne date code (string).
    """
    alphabet = {0:"A", 1:"B", 2:"C", 3:"D", 4:"E", 5:"F", 6:"G", 7:"H", \
                8:"I", 9:"J", 10:"K", 11:"L", 12:"M", 13:"N", 14:"O", \
                15:"P", 16:"Q", 17:"R", 18:"S", 19:"T", 20:"U", 21:"V", \
                22:"W", 23:"X", 24:"Y", 25:"Z", 26:"+"}
    if not (user_date):
        now = datetime.now()
    else:
        dsplit = user_date.split('-')
        now = datetime(int(dsplit[-1]),  int(dsplit[-2]), int(dsplit[-3]))
    year = now.year
    month = now.month
    day = now.day
    if(print_gregorian):
        print("Gregorian date: {}-{:02d}-{:02d}".format(year, month, day))


    day_of_year = now.timetuple().tm_yday - 1
    al_key = day_of_year // 14

    svanne = "{:02d}{}{:02d}".format(year-incept,
                                      alphabet[al_key],
                                      day_of_year%14) 
    if(print_svanne):
        print("Svanne date: {}".format(svanne))
    return svanne


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="")
    parser.add_argument("-i", "--inception", type=int, default=2022,
                        help="Inception year of repository")
    parser.add_argument("-d", "--date", type=str, default=None,
                        help="Date to convert. Must be in dd-mm-yyyy format.")
    parser.add_argument("-npg", "--no_print_gregorian", action="store_false",
                        help="Dont print Gregorian date format.")
    parser.add_argument("-nps", "--no_print_svanne", action="store_false",
                        help="Dont print Svanne date format.")

    args = parser.parse_args()
    incept = args.inception
    ucd = args.date
    pgreg = args.no_print_gregorian
    psvan = args.no_print_svanne

    get_svanne(incept, print_gregorian=pgreg, print_svanne=psvan, user_date=ucd)
