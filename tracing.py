import sys
assert sys.version_info >= (3, 2)

import os
import argparse
import json
from datetime import datetime
from urllib.request import Request, urlopen

def get_secrets():
    secrets = {}
    try:
        secrets['GITLAB_URL'] = os.environ['GITLAB_URL']
        secrets['GITLAB_PRIVATE_TOKEN'] = os.environ['GITLAB_PRIVATE_TOKEN']
    except:
        with open('.secrets.json') as secrets_file:
            secrets = json.load(secrets_file)
    
    return secrets

secrets = get_secrets()

def get_available_cnames():
    return [
        'thread_state_uninterruptible',
        'thread_state_iowait',
        'thread_state_running',
        'thread_state_runnable',
        #'thread_state_sleeping', # too bright
        'thread_state_unknown',
        'background_memory_dump',
        'light_memory_dump',
        'detailed_memory_dump',
        'vsync_highlight_color',
        'generic_work',
        'good',
        'bad',
        'terrible',
        #'black', # too dark
        #'grey', # too bright
        #'white', # too bright
        'yellow',
        'olive',
        'rail_response',
        'rail_animation',
        'rail_idle',
        'rail_load',
        'startup',
        'heap_dump_stack_frame',
        'heap_dump_object_type',
        'heap_dump_child_node_arrow',
        'cq_build_running',
        'cq_build_passed',
        'cq_build_failed',
        'cq_build_abandoned',
        'cq_build_attempt_runnig',
        'cq_build_attempt_passed',
        'cq_build_attempt_failed'
    ]


class RunnerColorMap:
    def __init__(self):
        self.next_index = 0
        self.runner_index_dict = {}

    def get_cname(self, runner_id, runner_system_id):
        key = str(runner_id) + '.' + str(runner_system_id)
        if key in self.runner_index_dict:
            index = self.runner_index_dict[key]
        else:
            index = self.next_index
            self.next_index += 1
            self.runner_index_dict[key] = index
        
        available_colors = get_available_cnames()
        return available_colors[index % len(available_colors)]   


def request_jobs_from_api(project_id, pipeline_id):
    jobs = []
    current_page = 1
    per_page = 50
    while current_page:
        url = secrets['GITLAB_URL'] + f"/api/v4/projects/{project_id}/pipelines/{pipeline_id}/jobs"
        params = f"page={current_page}&per_page={per_page}"
        req = Request(url + '?' + params)
        req.add_header('PRIVATE-TOKEN', secrets['GITLAB_PRIVATE_TOKEN'])
        response = urlopen(req)
        jobs += json.loads(response.read())
        response_info = dict(response.info())
        current_page = response_info['X-Next-Page']
    
    return jobs


parser = argparse.ArgumentParser()
parser.add_argument('project', help='project ID in gitlab')
parser.add_argument('pipeline', help='pipeline ID in gitlab')
parser.add_argument('--out-file', help='generate output to file')
parser.add_argument('--to-stdout', help='generate output to standard output', action='store_true')
args = parser.parse_args()

project_id = args.project
pipeline_id = args.pipeline

jobs = request_jobs_from_api(project_id, pipeline_id)

finished_jobs = []
for job in jobs:
    if job['started_at'] is None:
        continue

    if job['finished_at'] is None:
        sys.stderr.write("Warning: Job " + job['name'] + " has not finished yet - ignoring.\n")
        continue
    
    finished_jobs.append(job)


finished_jobs.sort(key=lambda job: job['started_at'])

events = []

thread_id = 1
runner_color_map = RunnerColorMap()

for job in finished_jobs:
    name = job['name']
    stage = job['stage']

    if job['started_at'] is None:
        continue

    if job['finished_at'] is None:
        sys.stderr.write(f"Warning: Job {name} has not finished yet - ignoring.\n")
        continue

    event_name = f"{name} ({stage})"
    started_at_timestamp = datetime.strptime(job['started_at'], "%Y-%m-%dT%H:%M:%S.%fZ").timestamp()
    finished_at_timestamp = datetime.strptime(job['finished_at'], "%Y-%m-%dT%H:%M:%S.%fZ").timestamp()
    duration = finished_at_timestamp - started_at_timestamp
    runner_id = job['runner']['id']
    runner_system_id = job['runner_manager']['system_id']
    cname = runner_color_map.get_cname(runner_id, runner_system_id)

    event_args = {
        'stage': stage,
        'runner_id': runner_id,
        'runner_system_id': runner_system_id,
        'duration': job['duration'],
        'queued_duration': job['queued_duration'],
        'tags': job['tag_list']
    }

    if 'artifacts_file' in job:
        event_args['artifact_filename'] = job['artifacts_file']['filename']
        event_args['artifact_size'] = job['artifacts_file']['size']
        event_args['artifact_size_human'] = str(round(job['artifacts_file']['size'] / 1024 / 1024, 2)) + " MiB"

    events.append(
        {
            "name": event_name,
            "cat": "job",
            "ph": "X",
            "ts": started_at_timestamp * 1000 * 1000,
            "dur": duration * 1000 * 1000,
            "pid": 0,
            "tid": thread_id,
            "cname": cname,
            "args": event_args
        }
    )

    thread_id += 1


if args.to_stdout:
    out_filepath = None
elif args.out_file:
    out_filepath = args.out_file
else:
    out_filepath = f"pipeline_trace_{project_id}_{pipeline_id}.json"

def get_output_stream(out_filepath):
    if out_filepath is None:
        return sys.stdout
    else:
        return open(out_filepath, 'w')

with get_output_stream(out_filepath) as f:
    json.dump(events, f, indent=2)

if out_filepath:
    print('Success: ' + out_filepath)
    print('Load file in chrome://tracing/ or https://ui.perfetto.dev/')