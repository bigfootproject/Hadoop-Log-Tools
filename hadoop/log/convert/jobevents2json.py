#!/usr/bin/env python
from __future__ import print_function

import argparse
import json
import os
import os.path as path
import sys

from libjobevent import parse_event

i_help="""The hadoop event file for the job.
When a job complete its event file can be found inside the directory 
<JobTracker>:/HADOOP_PATH/logs/history/done/.../.../.../.../.../<job_event_file>
"""

def parse_args(args):
  p = argparse.ArgumentParser()
  p.add_argument('-i','--input-files',help=i_help,nargs='+'
                     ,type=argparse.FileType('rt'),required=True
                     ,metavar='<job_event_file>')
  p.add_argument('-o','--output-dir'
                ,help='The output dir (default=stdout)'
                ,required=False)
  return p.parse_args(args)

def main():
  args = parse_args(sys.argv[1:])

  for input_file in args.input_files:
    sys.stderr.write('Parsing {}...'.format(input_file.name))
    events = map(parse_event, input_file.read().split(os.linesep))

    job = { 'maps' : {}, 'reduces' : {} }
    jobid = None
    for (event_words,event) in events:
      if not event_words:
        print('error: it doesn\t contain the events of a job')
        continue
      event_type = event_words[0]
      if event_type == 'Job':
        if jobid is None and 'JOBID' in event:
          jobid = event['JOBID']
        for key in ['JOBNAME','SUBMIT_TIME','LAUNCH_TIME','FINISH_TIME']:
          if not key in job and key in event:
            job[key.lower()] = event[key]
      elif event_type == 'Task':
        task_type = event['TASK_TYPE']
        if task_type != 'MAP' and task_type != 'REDUCE':
          continue
        tasks = job['maps' if event['TASK_TYPE'] == 'MAP' else 'reduces']
        task_id = event['TASKID']
        if task_id in tasks:
          task = tasks[task_id]
        else:
          task = { 'successful_attempt' : {} , 'other_attempts' : {} }
          tasks[task_id] = task
        for key in ['START_TIME','FINISH_TIME']:
          if not key in job and key in event:
            task[key.lower()] = event[key]
      elif event_type == 'MapAttempt' or event_type == 'ReduceAttempt':
        if not 'TASK_STATUS' in event:
          continue
        task_id = event['TASKID']
        attempt_id = event['TASK_ATTEMPT_ID']
        attempt_data = {}
        task_type = event['TASK_TYPE']
        if task_type != 'MAP' and task_type != 'REDUCE':
          continue
        is_map = task_type == 'MAP'
        tasks = job['maps' if is_map else 'reduces']
        task = tasks[task_id]
        if event['TASK_STATUS'] == 'SUCCESS':
          task['successful_attempt'] = { attempt_id : attempt_data }
        else:
          if 'other_attempts' in task:
            task['other_attempts'][attempt_id] = attempt_data
          else:
            task['other_attempts'][attempt_id] = { attempt_id : attempt_data }
        for key in ['HOSTNAME','SORT_FINISHED','SHUFFLE_FINISHED']:
          if key in event:
            attempt_data[key.lower()] = event[key]
    if not jobid:
      print('error: it doesn\'t contain the events of a job')
      continue
    if args.output_dir:
      if not path.isdir(args.output_dir):
        os.mkdir(args.output_dir)
      out_stream = open(path.join(args.output_dir,jobid+'.json'),'wt')
    else:
      out_stream = sys.stdout

    json.dump({ jobid : job }
               ,out_stream
               ,sort_keys=True
               ,indent=2
               , separators=(',', ': '))
    if args.output_dir:
      out_stream.close()
    sys.stderr.write('done{}'.format(os.linesep))

if __name__=='__main__':
  main()
