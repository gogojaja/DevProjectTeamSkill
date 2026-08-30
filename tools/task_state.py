#!/usr/bin/env python3
"""
Simple task state CLI for DevProjectTeamSkill.
Provides a minimal local task-state manager to track tasks and checkpoints.
"""
import argparse
import json
import os
import datetime

ROOT = os.environ.get("PROJECT_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STATE_FILE = os.path.join(ROOT, 'tools', 'task_state.json')

DEFAULT_STATE = {
    "tasks": []
}


def load_state():
    if not os.path.exists(STATE_FILE):
        return DEFAULT_STATE.copy()
    with open(STATE_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_state(state):
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def now():
    return datetime.datetime.now().isoformat()


def add_task(args):
    state = load_state()
    task = {
        'id': args.id,
        'title': args.title,
        'status': 'pending',
        'created_at': now(),
        'updated_at': now(),
        'notes': args.notes or ''
    }
    state['tasks'].append(task)
    save_state(state)
    print(json.dumps(task, ensure_ascii=False, indent=2))


def list_tasks(_args):
    state = load_state()
    print(json.dumps(state['tasks'], ensure_ascii=False, indent=2))


def update_task(args):
    state = load_state()
    for t in state['tasks']:
        if t['id'] == args.id:
            if args.title:
                t['title'] = args.title
            if args.status:
                t['status'] = args.status
            if args.notes is not None:
                t['notes'] = args.notes
            t['updated_at'] = now()
            save_state(state)
            print(json.dumps(t, ensure_ascii=False, indent=2))
            return
    print('task not found', args.id)


def delete_task(args):
    state = load_state()
    before = len(state['tasks'])
    state['tasks'] = [t for t in state['tasks'] if t['id'] != args.id]
    if len(state['tasks']) < before:
        save_state(state)
        print('deleted', args.id)
    else:
        print('task not found', args.id)


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers()

    p_add = sub.add_parser('add')
    p_add.add_argument('id')
    p_add.add_argument('title')
    p_add.add_argument('--notes')
    p_add.set_defaults(func=add_task)

    p_list = sub.add_parser('list')
    p_list.set_defaults(func=list_tasks)

    p_upd = sub.add_parser('update')
    p_upd.add_argument('id')
    p_upd.add_argument('--title')
    p_upd.add_argument('--status', choices=['pending', 'running', 'blocked', 'review', 'done'])
    p_upd.add_argument('--notes')
    p_upd.set_defaults(func=update_task)

    p_del = sub.add_parser('delete')
    p_del.add_argument('id')
    p_del.set_defaults(func=delete_task)

    args = p.parse_args()
    if not hasattr(args, 'func'):
        p.print_help()
        return
    args.func(args)


if __name__ == '__main__':
    main()
