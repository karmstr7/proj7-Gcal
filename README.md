# README

## Project 7: Google Calendar API 
## Authors:
#### Michal Young
#### Revised by: Keir Armstrong

#### About:
- Become familiar with Google Calendar API and OAuth2.
- A web app which takes calendars from one or more Google Calendar users and compute their mutual free-time in a given time frame. 
- No data is permanently stored (without a database).

#### Activation:
- In /memos create a credentials.ini file, and fill in the following variables:
    1. SECRET_KEY
    2. PORT
    3. GOOGLE_KEY_FILE
- Where
    1. SECRETE_KEY can be anything more than 0 length long,
    2. PORT can be anything between 1024-65535,
    3. GOOGLE_KEY_FILE is a file name provided by Google API Console.
- After credentials.ini has been created,
enter 'make install' under the main directory to install virtual environment.
- Enter 'make start' to start the server.
- Enter 'make stop' to stop the server from running.
- Enter 'make test' to run test cases.
