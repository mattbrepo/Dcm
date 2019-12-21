import os
import shutil
import sqlite3
import traceback

#
# Find all files in a directory
def find_all_files(base_dir):
  return [f for f in os.listdir(base_dir) if os.path.isfile(os.path.join(base_dir, f))]

#
# Find files with multiple pattern (es: find_files(., ('.txt', '.doc'))
def find_files(base_dir, pattern_tuple):
  for root, dirs, files in os.walk(base_dir):
    for basename in files:
      if basename.endswith(pattern_tuple):
        rel_filepath = os.path.join(root, basename)
        yield rel_filepath.strip(base_dir)

#
# Safe copy file
def safe_copy(src_filepath, dst_path):
  try:
    #copyfile(src_filepath, dst_path) #from shutil import copyfile
    shutil.copy(src_filepath, dst_path)
    return True
  except Exception as ex:
    #traceback.print_exc() #pro-debug
    return False

#
# Safe remove file
def safe_remove(filepath):
  try:
    os.remove(filepath)
  except OSError as e:
    pass

#
# DB quote string
def quote_str(str):
  if len(str) == 0:
    return "''"
  if len(str) == 1:
    if str == "'":
      return "''''"
    else:
      return "'%s'" % str
  if str[0] != "'" or str[-1:] != "'":
    return "'%s'" % str.replace("'", "''")
  return str

#
# DB quote on a list
def quote_list(l):
  return [quote_str(x) for x in l]

#
# DB quote on a list + join
def quote_list_as_str(l):
  return ','.join(quote_list(l))

#
# select on sqlite db
def select_db(db_conn, sql):
  cur = db_conn.cursor()
  cur.execute(sql)
  return cur.fetchall()

#
# one column select on sqlite db
def select1c_db(db_conn, sql):
  rows = select_db(db_conn, sql)
  return [row[0] for row in rows]

#
# convert tuple to string in my clean way
def tuple_to_str(t):
  #fatto con loop per togliere virgole da nomi file...
  #s = str(t)
  #return s.strip('(').strip(')').replace("'", '')
  res = ''
  for s in t:
    res = res + str(s).replace(',', '') + ', '
  return res[:-2]
  
#
# get sql AND/OR statement with quoted string
def get_sql_andor_quoted(case_sensitive, col_name, value, andFlag):
  if value == '':
    return ''
  
  if not case_sensitive:
    col_name = 'UPPER(' + col_name + ')'
    value = value.upper()
    
  and_or = ' AND ' if andFlag else ' OR '

  if '%' in value:
    return and_or + col_name + ' LIKE ' + quote_str(value)

  return and_or + col_name + ' = ' + quote_str(value)

#
# Search a string in a file (txt/pdf)
def search_string_in_file(filepath, words, case_insesitve):
  #--- file ext
  filename, file_extension = os.path.splitext(filepath)
  
  #--- pdf
  tmp_filepath = '~tmp.tmp'
  safe_remove(tmp_filepath)
  if file_extension == '.pdf':
    cmd = 'pdftotext.exe -nopgbrk "' + filepath + '" ' + tmp_filepath
    #print(cmd)
    os.system(cmd)
    filepath = tmp_filepath

  # text, pdf
  res = False
  if case_insesitve:
    words = words.lower()
    with open(filepath, 'r') as file:
      for line in file:
        if words in line.lower():
          res = True
          break
  else:
    with open(filepath, 'rb', 0) as file, mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ) as s:
      xs = bytes(words, 'utf8')
      if s.find(xs) != -1:
        res = True
  
  safe_remove(tmp_filepath)
  return res
