#!/bin/env python3
import pymsgbox
import time
from datetime import datetime, date
import yaml
import re
try:
    from yaml import CLoader as YamlLoader, CDumper as YamlDumper
except ImportError:
    from yaml import Loader as YamlLoader, Dumper as YamlDumper
import os
from collections import OrderedDict, defaultdict
# https://stackoverflow.com/a/50181505/5178528
yaml.add_representer(
    OrderedDict,
    lambda dumper,
    data: dumper.represent_mapping(
        'tag:yaml.org,2002:map',
        data.items()
    )
)
yaml.add_representer(
    defaultdict,
    lambda dumper,
    data: dumper.represent_mapping(
        'tag:yaml.org,2002:map',
        data.items()
    )
)
yaml.add_representer(
    set,
    lambda dumper,
    data: dumper.represent_sequence(
        'tag:yaml.org,2002:seq',
        list(data)
    )
)

try:
    from config import settings
except Exception as e:
    if not os.path.exists('config.py'):
        from shutil import copyfile
        copyfile('config.py.default', 'config.py')
        print(
            "A new config.py file has been created,"
            " ensure the settings are correct."
        )
        from config import settings
    else:
        raise e


logs = OrderedDict()
logs_path = settings.get('logs_path', 'logs')
SLEEP = settings.get('seconds_per_nag', 500)
date_format = settings.get('date_format', '%Y-%m-%d')
time_format = settings.get('time_format', '%H:%M:%S')
tags_format = settings.get('tags_format', '#')
ctx_format = settings.get('ctx_format', '@')
datetime_format = f"{date_format} {time_format}"
tags_regex = fr'{tags_format}[^\s#]*'
ctx_regex = fr'{ctx_format}[^\s#]*'


def parse_tags(content):
    tags = re.findall(tags_regex, content)
    return tags


def parse_ctx(content):
    ctx = re.findall(ctx_regex, content)
    return ctx


def get_time():
    return datetime.now().time().replace(
        microsecond=0).isoformat()


def from_str(str_date, date_format=time_format):
    if not isinstance(str_date, str):
        return str_date
    return datetime.strptime(str_date, date_format)


def to_str(src_date, date_format=time_format):
    if isinstance(src_date, str):
        return src_date
    return datetime.strftime(src_date, date_format)


def prep_data_struct(data, key=date.today()):
    if key in ['tags', 'ctx']:
        if key not in data:
            data[key] = set()
        else:
            data[key] = set(data[key])
    else:
        # FIXME: test if it is a date
        str_date = to_str(key, date_format)
        if not data.get(str_date):
            data[str_date] = {}
        struct = data[str_date]
        # FIXME: needs cleanup
        struct['logs'] = OrderedDict(struct.get('logs', ()))
        struct['tags'] = set(struct.get('tags', []))
        struct['ctx'] = set(struct.get('ctx', []))
        struct['reports'] = defaultdict(float, struct.get('reports', {}))
    return data


def log_entry(
        data,
        entry,
        current_date=date.today()
):
    time_in = entry.get('time_in')
    prep_data_struct(data)
    # TODO: use a counter
    # TODO: track common keywords
    tags = set(entry.get('tags', []))
    ctx = set(entry.get('ctx', []))
    str_date = to_str(current_date, date_format)
    entry['tags'] = tags
    entry['ctx'] = ctx
    data['tags'].update(
        tags
    )
    data['ctx'].update(ctx)
    for _ctx in ctx:
        data[str_date]['reports'][_ctx] += entry.get('delta', 0)
    for _tag in tags:
        data[str_date]['reports'][_tag] += entry.get('delta', 0)
    data[str_date]['logs'][time_in] = entry
    return data


def popup(last_entry=None):
    answer = (
        pymsgbox.prompt('what are you doing now ?')
        or "NO ANSWER"
    ).strip()
    new_time_in = to_str(get_time())
    if last_entry and not last_entry.get('time_out'):
        last_entry['delta'] = (
            from_str(new_time_in)
            - from_str(last_entry['time_in'])
        ).total_seconds() / 60.0
        last_entry['time_out'] = new_time_in
    tags = parse_tags(answer)
    ctx = parse_ctx(answer)
    return {
        'time_in': new_time_in,
        'tags': tags,
        'ctx': ctx,
        'content': answer,
    }


def load_yaml(data, loader=YamlLoader):
    return yaml.load(
        data,
        Loader=loader
    )


def dump_yaml(data, dumper=YamlDumper):
    return yaml.dump(
        data,
        Dumper=dumper
    )


def todays_log(today=date.today()):
    return os.path.join(
        logs_path,
        f"{today}.yml"
    )


def prep_log_path(load_date=date.today()):
    if not os.path.exists(logs_path):
        os.makedirs(logs_path)
    return todays_log(load_date)


def load_log(load_date=date.today()):
    log = prep_log_path(load_date)
    if os.path.exists(log):
        data = open(log, 'r').read()
        return load_yaml(data)
    return {}


def save_log(data, dump_date=date.today()):
    log = prep_log_path(dump_date)
    f = open(log, 'w')
    f.write(dump_yaml(data))
    f.close()


def loop_popup(
        data,
        logfile=date.today(),
        sleep=SLEEP,
        stop=-1
):
    prev_entry = None
    while stop != 0:
        if stop > 0:
            stop -= 1
        entry = popup(prev_entry)
        if prev_entry:
            log_entry(
                data,
                prev_entry,
            )
        prev_entry = entry
        log_entry(
            data,
            entry,
        )
        save_log(
            data,
            logfile
        )
        time.sleep(sleep)


def report_date(data, report_date=date.today()):
    str_date = to_str(report_date, date_format)


if __name__ == '__main__':
    # TODO: create one file per day
    # TODO: add reporting function
    # TODO: catch exit to add date as final timeout
    # TODO: accept options (ie: nb sec wait)
    logfile = "global"
    data = load_log(logfile) or {}
    prep_data_struct(data, 'tags')
    prep_data_struct(data, 'ctx')
    loop_popup(data, logfile)
    # debug
    # loop_popup(data, logfile, 1, 3)
