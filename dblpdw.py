#!/usr/bin/env python3

import sys
import argparse
import pathlib
import csv
import urllib.request
import bibtexparser
from pathlib import Path
from bibtexparser.bibdatabase import BibDatabase
from bibtexparser.bwriter import BibTexWriter


class Author:
    pid = None
    name = None
    __pubs_db = None

    def __init__(self, pid, name):
        self.pid = pid
        self.name = name

    def get_publications_db(self):
        if self.__pubs_db is None:
            url = 'https://dblp.org/pid/' + self.pid + '.bib'
            with urllib.request.urlopen(url) as response:
                raw_bib = response.read().decode('utf-8')
                self.__pubs_db = PublicationsDb(bibtexparser.loads(raw_bib))
        return self.__pubs_db

    def as_dict(a):
        return { 'pid' : a.pid, 'name' : a.name }

class AuthorsDb:
    __authors = {}
    __path = None

    def __init__(self, path):
        self.__path = Path(path)

    def get_authors(self):
        return sorted(list(self.__authors.values()), key=lambda a: a.name)

    def get_author(self, pid):
        return self.__authors.get(pid)
    
    def add_author(self, pid, name):
        self.__authors[pid] = Author(pid, name)

    def del_author(self, pid):
        self.__authors.pop(pid)

    def load(self):
        if not self.__path.is_file():
            self.save()
            return
        with self.__path.open(mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(filter(lambda row: row.strip() != '' and row.strip()[0] != '#', file))
            for line in reader:
                name = line['author'].strip()
                pid  = line['pid'].strip()
                self.add_author(pid, name)

    def save(self):
        with self.__path.open(mode='w', encoding='utf-8') as file:
            print(
'''# Lines starting with '#' are comments
# Empty lines are ignored
#
# Any manually introduced comment or empty line will be deleted between executions!!
# 
# IMPORTANT: The first non-empty, uncommented line MUST BE "author,pid"

author,pid
''', file=file)
            for author in sorted(self.get_authors(), key=lambda a: a.name):
                print('"{}","{}"'.format(author.name, author.pid), file=file)

class PublicationsDb:
    __bib_db = None

    def __init__(self, bib_db):
        self.__bib_db = bib_db

    def in_period(self, start_year, end_year):
        filtered_db = BibDatabase()
        for entry in self.__bib_db.get_entry_list():
            if int(entry['year']) >= start_year and int(entry['year']) <= end_year:
                filtered_db.entries.append(entry)
        return PublicationsDb(filtered_db)

    def to_string(self):
        if len(self.__bib_db.get_entry_list()) == 0:
            return ''
        writer = BibTexWriter()
        writer.align_multiline_values = True
        writer.align_values = True
        writer.order_entries_by = ('year', 'ENTRYTYPE')
        return bibtexparser.dumps(self.__bib_db, writer)

    def save_to(self, path):
        if len(self.__bib_db.get_entry_list()) == 0:
            return
        with open(path, mode='w', encoding='utf-8') as file:
            writer = BibTexWriter()
            writer.align_multiline_values = True
            writer.align_values = True
            writer.order_entries_by = ('year', 'ENTRYTYPE')
            bibtexparser.dump(self.__bib_db, file, writer)
    
def build_args_parser():
    parser = argparse.ArgumentParser(description='Download publications as BibTeX from DBLP')
    parser.add_argument('-a', '--authors-file',
                        required=True,
                        type=pathlib.Path,
                        help='Authors file, containing the author\'s names and their DBLP keys in CSV. An empty file will be created if the given file does not exist.')
    parser.add_argument('-o', '--output-file',
                        required=False,
                        type=pathlib.Path,
                        help='Output file. If not specified, results will be shown in stdout')
    parser.add_argument('-s', '--start-year',
                        required=False,
                        type=int,
                        default=0,
                        help='start year')
    parser.add_argument('-e', '--end-year',
                        required=False,
                        type=int,
                        default=9999,
                        help='end year')
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)
    return parser



def main():
    args = build_args_parser().parse_args()

    authors_db = AuthorsDb(args.authors_file)
    authors_db.load()
    
    if args.output_file is not None:
        file = open(args.output_file, mode='w', encoding='utf-8')
    else:
        file = sys.stdout
        
    for author in authors_db.get_authors():
        filtered_db = author.get_publications_db().in_period(args.start_year, args.end_year)
        file.write(filtered_db.to_string())
        file.write('\n')
    
    if args.output_file is not None:
        file.close()
    
    authors_db.save()
    

if __name__ == '__main__':
    main()