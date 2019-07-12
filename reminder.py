#!/bin/env python3
import pymsgbox
import time
from datetime import datetime, date, timedelta
from itertools import product
import yaml
import re
import sys
try:
    from yaml import CLoader as YamlLoader, CDumper as YamlDumper
except ImportError:
    from yaml import Loader as YamlLoader, Dumper as YamlDumper
import os
from collections import OrderedDict, defaultdict
# https://stackoverflow.com/a/50181505/5178528
# https://stackoverflow.com/a/56808359/5178528
yaml.representer.SafeRepresenter.add_representer(
    OrderedDict,
    lambda dumper, data: dumper.represent_mapping(
        'tag:yaml.org,2002:map',
        data.items()
    )
)
yaml.representer.SafeRepresenter.add_representer(
    defaultdict,
    lambda dumper, data: dumper.represent_mapping(
        'tag:yaml.org,2002:map',
        data.items()
    )
)
yaml.representer.SafeRepresenter.add_representer(
    set,
    lambda dumper, data: dumper.represent_sequence(
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
tags_regex = fr'{tags_format}[^\s]*'
ctx_regex = fr'{ctx_format}[^\s]*'
uptime_format = settings.get('uptime_format', '+')
uptime_regex = fr'\+([0-9]+)([dhm])'


def parse_tags(content):
    tags = re.findall(tags_regex, content)
    return tags


def parse_ctx(content):
    ctx = re.findall(ctx_regex, content)
    return ctx


def parse_uptime(content):
    # TODO: use something like re.sub("[^\d\.]", "", value) to cleanup
    values = {
        'h': ['hours', ],
        'm': ['minutes', ],
        'd': ['days', ],
    }
    uptime = re.findall(uptime_regex, content)
    d = timedelta()
    for delta in uptime:
        val = values.get(delta[1])
        val.append(float(delta[0]))
        d += timedelta(**dict([val]))
    return d.total_seconds() / 60.0


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
    tags_set = set(tags)
    entry['tags'] = tags_set
    stripped = set([''.join(x.split('-', 1)[:1]) for x in tags_set])
    entry['ctx'] = set(ctx)
    data['tags'].update(
        tags
    )
    data['ctx'].update(ctx)
    reports = data[str_date]['reports']
    delta = entry.get('delta', 0)
    for _ctx in ctx:
        reports[_ctx] += delta
    for _tag in tags:
        reports[_tag] += delta
    # for _stripped in stripped:
    #     reports[f"total_{_stripped}"] += delta
    # Combine context with base keyword
    context_report = list(
        map(
            lambda x: '-'.join(x),
            product(ctx, stripped)
        )
    )
    for rep in context_report:
        reports[rep] += delta

    data[str_date]['logs'][time_in] = entry
    return data


def popup(last_entry=None):
    answer = (
        pymsgbox.prompt('what are you doing now ?')
        or "NO ANSWER"
    ).strip()
    new_time_in = to_str(get_time())
    if last_entry and not last_entry.get('time_out'):
        uptime = parse_uptime(last_entry['content'])
        last_entry['delta'] += uptime
        last_entry['delta'] += (
            from_str(new_time_in)
            - from_str(last_entry['time_in'])
        ).total_seconds() / 60.0
        last_entry['time_out'] = new_time_in
    tags = parse_tags(answer)
    ctx = parse_ctx(answer)
    return {
        'delta': 0,
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
    return yaml.safe_dump(
        data,
        # Dumper=dumper
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
    kill = False
    while stop != 0:
        if stop > 0:
            stop -= 1
        try:
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
            if kill:
                sys.exit(0)
            if stop != 0:
                time.sleep(sleep)
        except KeyboardInterrupt as e:
            kill = True
            stop = 1


def report_date(data, report_date=date.today()):
    str_date = to_str(report_date, date_format)


if __name__ == '__main__':
    # TODO: create one file per day
    # TODO: accept options (ie: nb sec wait)
    # TODO: add autocomplete of tags and contexts
    # TODO: add autocomplete of tags based on other tags/contexts
    logfile = "global"
    data = load_log(logfile) or {}
    prep_data_struct(data, 'tags')
    prep_data_struct(data, 'ctx')

    loop_popup(data, logfile)
    # debug
    # loop_popup(data, logfile, 1, 3)
