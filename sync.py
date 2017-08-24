import taskw
from pytodoist import todoist
import peewee
from playhouse import sqlite_ext

import uuid
import datetime
import os

TODOIST_API_TOKEN = os.environ.get("TODOIST_API_TOKEN")

TODOIST_DEFAULT_PROJECT = "Inbox"
SKIP_TODOIST_PROJECT_NAMES = ['Alexa Shopping List',]

if TODOIST_API_TOKEN is None:
    raise Exception("Please set your Todoist API token in the TODOIST_API_TOKEN environment variable")

db = sqlite_ext.SqliteDatabase('sync.db')

class TodoistTaskWarrierSyncModel(peewee.Model):
    taskwarrier = peewee.UUIDField()
    todoist = peewee.IntegerField(unique=True)
    created_on = peewee.DateTimeField(default=datetime.datetime.now)
    completed = peewee.BooleanField(default=False)

    class Meta:
        database = db

db.connect()
try:
    db.create_tables([TodoistTaskWarrierSyncModel,])
except peewee.OperationalError as e:
    if "already exists" in e.message:
        pass
    else:
        raise

def ti_task_synced_to_tw(ti_task):
    try:
        TodoistTaskWarrierSyncModel.get(todoist=ti_task.id)
        return True
    except TodoistTaskWarrierSyncModel.DoesNotExist:
        return False

def tw_task_synced_to_ti(tw_task):
    try:
        TodoistTaskWarrierSyncModel.get(taskwarrier=tw_task['uuid'])
        return True
    except TodoistTaskWarrierSyncModel.DoesNotExist:
        return False

def create_tw_task(ti_task, tw_cli):
    project_name = ti_task.project.name
    if project_name == "Inbox":
        project_name = None
    tw_task = tw_cli.task_add(ti_task.content, project=project_name)

    sync_rec = TodoistTaskWarrierSyncModel.create(
        todoist=ti_task.id,
        taskwarrier=tw_task['uuid'],
    )
    sync_rec.save()

    print u"added {} from todoist to taskwarrier".format(ti_task.content)

def create_ti_task(tw_task, ti_cli):
    project_name = tw_task.get('project', TODOIST_DEFAULT_PROJECT)
    ti_project = ti_cli.get_project(project_name)
    if ti_project is None:
        ti_project = ti_cli.add_project(project_name)
        print u"Added new todoist project `{}`".format(project_name)
    ti_task = ti_project.add_task(tw_task['description'])

    sync_rec = TodoistTaskWarrierSyncModel.create(
        todoist=ti_task.id,
        taskwarrier=tw_task['uuid'],
    )
    sync_rec.save()

    print u"added {} from todoist to taskwarrier".format(ti_task.content)


def mark_tw_task_complete(tw_task, tw_cli):
    tw_cli.task_done(id=tw_task['id'])
    print u"todoist -> taskwarrior: task `{}` done".format(tw_task['description'])


def mark_ti_task_complete(ti_id, ti_tasks, tw_task):
    for task in ti_tasks:
        if task.id == ti_id:
            task.complete()
            print u"taskwarrior -> todoist: task `{}` done".format(tw_task['description'])
            return

def main():
    tw_cli = taskw.TaskWarrior()
    ti_cli = todoist.login_with_api_token(TODOIST_API_TOKEN)

    ti_tasks = ti_cli.get_tasks()
    tw_tasks = tw_cli.load_tasks()

    # NOTE: todoist only returns uncompleted tasks whereas taskwarrier returns
    # all

    for ti_task in ti_tasks:
        if ti_task.project.name in SKIP_TODOIST_PROJECT_NAMES:
            continue

        if not ti_task_synced_to_tw(ti_task=ti_task):
            create_tw_task(ti_task=ti_task, tw_cli=tw_cli)

    for tw_task in tw_tasks['pending']:
        if not tw_task_synced_to_ti(tw_task=tw_task):
            create_ti_task(tw_task=tw_task, ti_cli=ti_cli)
        else:
            # check if task has been marked completed on todoist by seeing if
            # it's in the list returned from todoist
            sync_rec = TodoistTaskWarrierSyncModel.get(taskwarrier=tw_task['uuid'])
            if not sync_rec.completed:
                ti_id = sync_rec.todoist
                if not ti_id in map(lambda t: t.id, ti_tasks):
                    mark_tw_task_complete(tw_task=tw_task, tw_cli=tw_cli)
                sync_rec.update(completed=True)

    for tw_task in tw_tasks['completed']:
        if tw_task_synced_to_ti(tw_task=tw_task):
            sync_rec = TodoistTaskWarrierSyncModel.get(taskwarrier=tw_task['uuid'])
            if not sync_rec.completed:
                ti_id = sync_rec.todoist
                mark_ti_task_complete(ti_id=ti_id, ti_tasks=ti_tasks, tw_task=tw_task)
                sync_rec.update(completed=True)


if __name__ == "__main__":
    main()
