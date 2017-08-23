# Todoist <-> Taskwarrior sync

Simple command to sync local [Taskwarrior](https://taskwarrior.org)
installation with [Todoist](https://todoist.com).

*NOTE*: this utility uses a local sqlite database to keep a mapping of the
Taskwarrior and Todoist IDs given to a task.

## Setup

1. Install python requirements

    pip install -r requirements.txt

2. Get a Todoist API token on your [Todoist settings
page](https://todoist.com/Users/viewPrefs?page=authorizations)

3. Run sync command

    TODOIST_API_TOKEN=... python sync.py


## Contribute

Pull requests very welcome :)
