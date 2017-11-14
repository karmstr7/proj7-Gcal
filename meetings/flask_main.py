import flask
from flask import render_template
from flask import request

from calc_busy import get_busy_events
from _functools import reduce
import ast
import logging

# Date handling 
import arrow  # Replacement for datetime, based on moment.js
# import datetime # But we still need time

# OAuth2  - Google library implementation for convenience
from oauth2client import client
import httplib2  # used in oauth2 flow

# Google API for services 
from apiclient import discovery

###
# Globals
###
import config

if __name__ == "__main__":
    CONFIG = config.configuration()
else:
    CONFIG = config.configuration(proxied=True)

app = flask.Flask(__name__)
app.debug = CONFIG.DEBUG
app.logger.setLevel(logging.DEBUG)
app.secret_key = CONFIG.SECRET_KEY

SCOPES = 'https://www.googleapis.com/auth/calendar.readonly'
CLIENT_SECRET_FILE = CONFIG.GOOGLE_KEY_FILE  # You'll need this
APPLICATION_NAME = 'MeetMe class project'


#############################
#
#  Pages (routed from URLs)
#
#############################


@app.route("/")
@app.route("/index")
def index():
    return render_template('index.html')


@app.route("/choose")
def choose():
    # We'll need authorization to list calendars
    # I wanted to put what follows into a function, but had
    # to pull it back here because the redirect has to be a
    # 'return'
    app.logger.debug("Checking credentials for Google calendar access")
    credentials = valid_credentials()
    if not credentials:
        app.logger.debug("Redirecting to authorization")
        return flask.redirect(flask.url_for('oauth2callback'))

    gcal_service = get_gcal_service(credentials)
    app.logger.debug("Returned from get_gcal_service")
    flask.g.calendars = list_calendars(gcal_service)
    return render_template('index.html')


####
#
#  Google calendar authorization:
#      Returns us to the main /choose screen after inserting
#      the calendar_service object in the session state.  May
#      redirect to OAuth server first, and may take multiple
#      trips through the oauth2 callback function.
#
#  Protocol for use ON EACH REQUEST: 
#     First, check for valid credentials
#     If we don't have valid credentials
#         Get credentials (jump to the oauth2 protocol)
#         (redirects back to /choose, this time with credentials)
#     If we do have valid credentials
#         Get the service object
#
#  The final result of successful authorization is a 'service'
#  object.  We use a 'service' object to actually retrieve data
#  from the Google services. Service objects are NOT serializable ---
#  we can't stash one in a cookie.  Instead, on each request we
#  get a fresh serivce object from our credentials, which are
#  serializable. 
#
#  Note that after authorization we always redirect to /choose;
#  If this is unsatisfactory, we'll need a session variable to use
#  as a 'continuation' or 'return address' to use instead. 
#
####


def valid_credentials():
    """
    Returns OAuth2 credentials if we have valid
    credentials in the session.  This is a 'truthy' value.
    Return None if we don't have credentials, or if they
    have expired or are otherwise invalid.  This is a 'falsy' value. 
    """
    if 'credentials' not in flask.session:
        return None

    credentials = client.OAuth2Credentials.from_json(
        flask.session['credentials'])

    if credentials.invalid or credentials.access_token_expired:
        return None
    return credentials


def get_gcal_service(credentials):
    """
    We need a Google calendar 'service' object to obtain
    list of calendars, busy times, etc.  This requires
    authorization. If authorization is already in effect,
    we'll just return with the authorization. Otherwise,
    control flow will be interrupted by authorization, and we'll
    end up redirected back to /choose *without a service object*.
    Then the second call will succeed without additional authorization.
    """
    app.logger.debug("Entering get_gcal_service")
    http_auth = credentials.authorize(httplib2.Http())
    service = discovery.build('calendar', 'v3', http=http_auth)
    app.logger.debug("Returning service")
    return service


@app.route('/oauth2callback')
def oauth2callback():
    """
    The 'flow' has this one place to call back to.  We'll enter here
    more than once as steps in the flow are completed, and need to keep
    track of how far we've gotten. The first time we'll do the first
    step, the second time we'll skip the first step and do the second,
    and so on.
    """
    app.logger.debug("Entering oauth2callback")
    flow = client.flow_from_clientsecrets(
        CLIENT_SECRET_FILE,
        scope=SCOPES,
        redirect_uri=flask.url_for('oauth2callback', _external=True))
    # Note we are *not* redirecting above.  We are noting *where*
    # we will redirect to, which is this function.

    # The *second* time we enter here, it's a callback
    # with 'code' set in the URL parameter.  If we don't
    # see that, it must be the first time through, so we
    # need to do step 1.
    app.logger.debug("Got flow")
    if 'code' not in flask.request.args:
        app.logger.debug("Code not in flask.request.args")
        auth_uri = flow.step1_get_authorize_url()
        return flask.redirect(auth_uri)
    # This will redirect back here, but the second time through
    # we'll have the 'code' parameter set
    else:
        # It's the second time through ... we can tell because
        # we got the 'code' argument in the URL.
        app.logger.debug("Code was in flask.request.args")
        auth_code = flask.request.args.get('code')
        credentials = flow.step2_exchange(auth_code)
        flask.session['credentials'] = credentials.to_json()
        # Now I can build the service and execute the query,
        # but for the moment I'll just log it and go back to
        # the main screen
        app.logger.debug("Got credentials")
        return flask.redirect(flask.url_for('choose'))

####
#
#  Functions (NOT pages) that return some information
#
####


def list_calendars(service):
    """
    Given a google 'service' object, return a list of
    calendars.  Each calendar is represented by a dict.
    The returned list is sorted to have
    the primary calendar first, and selected (that is, displayed in
    Google Calendars web app) calendars before unselected calendars.
    """
    app.logger.debug("Entering list_calendars")
    calendar_list = service.calendarList().list().execute()["items"]
    result = []
    for cal in calendar_list:
        kind = cal["kind"]
        id = cal["id"]
        if "description" in cal:
            desc = cal["description"]
        else:
            desc = "(no description)"
        summary = cal["summary"]
        # Optional binary attributes with False as default
        selected = ("selected" in cal) and cal["selected"]
        primary = ("primary" in cal) and cal["primary"]
        result.append(
            {"kind": kind,
             "id": id,
             "summary": summary,
             "selected": selected,
             "primary": primary})
    return sorted(result, key=cal_sort_key)


def cal_sort_key(cal):
    """
    Sort key for the list of calendars:  primary calendar first,
    then other selected calendars, then unselected calendars.
    (" " sorts before "X", and tuples are compared piecewise)
    """
    if cal["selected"]:
        selected_key = " "
    else:
        selected_key = "X"
    if cal["primary"]:
        primary_key = " "
    else:
        primary_key = "X"
    return primary_key, selected_key, cal["summary"]


#################
#
# Ajax handlers
#
#################

@app.route("/set_range")
def set_range():
    """
    Set the chosen begin datetime and end datetime to their session cookies.
    :return: JSON-ed url path of /choose
    """
    app.logger.debug("ENTERING SET_RANGE")
    begin_datetime = request.args.get('begin_datetime')
    end_datetime = request.args.get('end_datetime')
    app.logger.debug("begin_datetime: {}, end_datetime: {}".format(begin_datetime, end_datetime))
    flask.session['begin_datetime'] = begin_datetime
    flask.session['end_datetime'] = end_datetime
    return flask.jsonify(redirect="/choose")


@app.route("/select")
def select():
    """
    Does things with the selected calendars.
    :return: A list of events impeding with the meeting time.
    """
    app.logger.debug("ENTERING SELECT")
    calendars = request.args.get('calendars', type=str)
    credentials = valid_credentials()
    if not credentials:
        app.logger.debug("Redirecting to authorization")
        return flask.redirect(flask.url_for('oauth2callback'))
    gcal_service = get_gcal_service(credentials)
    got_events = get_events(calendars, gcal_service)
    cal_busy = get_busy_events(got_events, flask.session['begin_datetime'], flask.session['end_datetime'])
    return flask.jsonify(result=cal_busy)


#################
#
# Get events from calendars and other event processing.
#
#################

def get_events(calendars, service):
    """
    Gets events from the chosen calendars.
    Converts all instances of ISO-8601 time strings from local to UTC.
    :param calendars:   A list of calendars
    :param service:     A service object, need this to grab events from the calendars.
    :return: A list of tuples containing useful information about the calendars' events.
    """
    app.logger.debug("Entering get_events")
    event_list = []
    calendars = ast.literal_eval(calendars)
    for calendar in calendars:
        calendar = ast.literal_eval(calendar)
        calendar_events = service.events().list(calendarId=calendar['id'], singleEvents=True).execute()['items']
        for calendar_event in calendar_events:
            if 'transparency' in calendar_event and calendar_event['transparency'] is "transparent":
                continue
            event_list.append(({"calendar": calendar['id']},
                               {"summary": calendar_event['summary']},
                               {"start": calendar_event['start']},
                               {"end": calendar_event['end']},
                               {"recurrence": reduce(lambda d, key: d.get(key) if d else None,
                                                     ['recurrence'],
                                                     calendar_event)}))
    for event in event_list:
        for attribute in event:
            if 'start' in attribute:
                try:
                    attribute['start']['dateTime'] = convert_to_utc(attribute['start']['dateTime'])
                    attribute['start']['timeZone'] = 'UTC'
                except KeyError:
                    continue
            if 'end' in attribute:
                try:
                    attribute['end']['dateTime'] = convert_to_utc(attribute['end']['dateTime'])
                    attribute['end']['timeZone'] = 'UTC'
                except KeyError:
                    continue
    return event_list


def convert_to_utc(tz_time):
    """
    :param tz_time: A dictionary object containing the start or end time of the event,
                    the time is an ISO string with timezone attached.
    :return:    An ISO-8601 string of time in UTC.
    """
    return str(arrow.get(tz_time).to('UTC'))


if __name__ == "__main__":
    # App is created above so that it will
    # exist whether this is 'main' or not
    # (e.g., if we are running under green unicorn)
    app.run(port=CONFIG.PORT, host="0.0.0.0")
