#!/usr/bin/env python3

import json
import time
import sys
import argparse
import pathlib
from dblpdw import Author, AuthorsDb
from flask import Flask, Response, request
from waitress import serve

app = Flask(__name__, static_url_path='')

@app.route('/authors')
def authors():
  return json.dumps(authors_db.get_authors(), cls=MyJSONEncoder);


@app.route('/author/<pid>', methods=['GET', 'PUT', 'DELETE'])
def author(pid):
  
  pid = pid.replace('-', '/')

  if request.method == 'GET':
    author = authors_db.get_author(pid)
    if author is not None:
      return Author.as_dict(author)
    else:
      return Response(status=404)
 
  elif request.method == 'PUT':
    if pid != request.json['pid']:
      return Response(status=400, response='Author data does not belong to this method')
    name = request.json['name']
    if authors_db.get_author(pid) is None:
      authors_db.add_author(pid, name)
    else:
      authors_db.get_author(pid).name = name
    authors_db.save()
    return Response(status=204)
    
  elif request.method == 'DELETE':
    if authors_db.get_author(pid) is None:
      return Response(status=404)
    else:
      authors_db.del_author(pid)
      authors_db.save()
      return Response(status=204)


@app.route('/publications/<comma_separated_pids>', methods=['GET'])
def publications(comma_separated_pids):
  
  start = request.args.get('start', 0, type = int)
  end = request.args.get('end', 9999, type = int)
  
  
  if request.method == 'GET':
    pids = comma_separated_pids.replace('-', '/').split(',')
    publications = []
    for pid in pids:
      author = authors_db.get_author(pid)
      if author is None:
        return Response(status=400, response='Author {} does not exist'.format(pid))
      else:
        # Wait 1 second between requests
        # as suggested in https://dblp.org/faq/Am+I+allowed+to+crawl+the+dblp+website.html
        time.sleep(1)
        publications.append(author.get_publications_db().in_period(start, end).to_string())
    return '\n'.join(publications)


@app.route('/')
def root():
  return app.send_static_file('index.html')


## End of routes

def build_args_parser():
    parser = argparse.ArgumentParser(description='Download publications as BibTeX from DBLP')
    parser.add_argument('-a', '--authors-file',
                        required=True,
                        type=pathlib.Path,
                        help='Authors file, containing the author\'s names and their DBLP keys in CSV. An empty file will be created if the given file does not exist.')
    parser.add_argument('-l', '--listening-address',
                        required=False,
                        default='127.0.0.1',
                        help='Listening address (defaults to 127.0.0.1 for security purposes)')
    parser.add_argument('-p', '--listening-port',
                        required=False,
                        type=int,
                        default=8000,
                        help='Listening port (defaults to 8000)')

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)
    return parser


class MyJSONEncoder(json.JSONEncoder):
  def default(self, o):
      if isinstance(o, Author):
          return Author.as_dict(o)
      return super().default(o)

if __name__ == '__main__':
  args = build_args_parser().parse_args()

  authors_db = AuthorsDb(args.authors_file)
  authors_db.load()

  serve(app, host=args.listening_address, port=args.listening_port)
