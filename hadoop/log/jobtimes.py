#!/usr/bin/env python
from __future__ import print_function,division

import argparse
import json
import sys

def parse_args(args):
  p = argparse.ArgumentParser(description='Extract job times')
  p.add_argument('-m','--num-maps',metavar=('MIN','MAX'),nargs=2
                ,required=False,type=int
                ,help='filter jobs with num maps > MIN and < MAX')
  p.add_argument('-r','--num-reduces',metavar=('MIN','MAX'),nargs=2
                ,required=False,type=int
                ,help='filter jobs with num reducers > MIN and < MAX')
  g = p.add_mutually_exclusive_group(required=True)
  g.add_argument('-p','--phase'
                     ,choices=['map','shuffle','sort','reduce','full_reduce']
                     ,help='the job phase to extract (full_reduce contains'
                          +' shuffle, sort and reduce time)')
  g.add_argument('-s','--sojourn-time',action='store_true',default=False)
  p.add_argument('-i','--input-files',metavar='INPUT_FILE'
                ,required=True, nargs='+',type=argparse.FileType('rt')
                ,help='files containing the job events in json format')
  p.add_argument('-t','--time-unit',default='seconds',choices=['seconds']
                ,help='time unit to be displayed (for future releases)')
  return p.parse_args(args)

def getdiff(time_unit):
  if time_unit == 'seconds':
    def f(t1,t2):
      return (float(t1)-float(t2)) / 1000
  return f

def main():
  args = parse_args(sys.argv[1:])
  diff = getdiff(args.time_unit)
  for input_file in args.input_files:
    job = json.load(input_file).values()[0]

    # filter by num of maps
    if args.num_maps:
      num_maps = len(job['maps'])
      if num_maps < args.num_maps[0] or num_maps > args.num_maps[1]:
        continue

    # filter by num of reducers
    if args.num_reduces:
      num_reduces = len(job['reduces'])
      if num_reduces < args.num_reduces[0] or num_reduces > args.num_reduces[1]:
        continue

    # print the sojourn time
    if args.sojourn_time:
      print(diff(job['finish_time'],job['submit_time']))
      continue
    
    # get a time task dependent
    tasks = job['maps' if args.phase == 'map' else 'reduces'].values()
    for task in tasks:

      # print the map or full_reduce time 
      if args.phase == 'map' or args.phase == 'full_reduce':
        print(diff(task['finish_time'],task['start_time']))
      else:
        attempt = task['successful_attempt'].values()[0]
        # print the sort time
        if args.phase == 'sort':
          print(diff(attempt['sort_finished'],attempt['shuffle_finished']))
        # print the shuffle time
        elif args.phase == 'shuffle':
          print(diff(attempt['shuffle_finished'],task['start_time']))
        # print the reduce computation time
        elif args.phase == 'reduce':
          print(diff(task['finish_time'],attempt['shuffle_finished']))

if __name__=='__main__':
  main()
