#
# Document content manager
#

import os
import sys
from colorama import init, Fore, Back, Style
import traceback
import pyperclip
from tabulate import tabulate
import dcm_util, dcm_issue, dcm_repo
import time

class Cmd:
  IKIND = 0
  IURL = 1
  ITITLE = 2
  ILANG = 3
  ILABELS = 4
  IKEYWORDS = 5

  PAR_ALL = '*'

  # --- environments
  ENV_ISSUES = 'issues'
  ENV_REPO = 'repo'
  ENV_LABELS = 'labels'

  # --- general commands
  CMD_HELP = 'help'
  CMD_SHOW = 'show'
  CMD_SELECT = 'sel'
  CMD_UNSELECT = 'unsel'

  # --- issues commands
  ISSUES_SCAN = 'scan'
  ISSUES_ADD_FILE_DB = 'addf'
  ISSUES_ADD_MUL_FILES_DB = 'maddf'
  ISSUES_DEL_MISSING_DB = 'del'
  ISSUES_ADD_BOOKMARK_DB = 'addb'
  ISSUES_IGNORE_FILE_DB = 'ignore'
  ISSUES_FIX_FILE_DB = 'fix'
  ISSUES_OPEN_FILE = 'open'

  # --- repo commands
  REPO_COLS = 'cols' # show/change shown column
  REPO_RESET = 'reset'
  REPO_WHERE = 'where'
  REPO_ORDER = 'ord'
  REPO_AND = 's_and'
  REPO_OR = 's_or'
  REPO_FILTER = 'filter'
  REPO_ANY = 'any'
  REPO_SEARCH = 'search'

  REPO_HTML = 'html' # export to html
  REPO_CSV = 'csv' # export to csv selected elements
  REPO_FAVORITE = 'favor' # show favorites
  
  #selected elements
  REPO_S_OPEN = 'open' # open file/url
  REPO_S_COPY = 'copy' # copy file
  REPO_S_COPY_DESK = 'copyd' # copy file to desktop
  REPO_S_CLIP = 'clip' # write on clipboard
  REPO_S_LABEL = 'lab' # toggle label
  REPO_S_TITLE = 'title' # change title
  REPO_S_DEL = 'del' # remove item from repo (file, bookmark)
  REPO_S_INFO = 'info' # extra info on file

  # --- labels commands
  LABELS_DEL = 'del'
  LABELS_RENAME = 'ren'

dcmEnv = Cmd.ENV_REPO # default environment
envEles = {Cmd.ENV_ISSUES: [], Cmd.ENV_REPO: [], Cmd.ENV_LABELS: []} # environment elements
selEles = {Cmd.ENV_ISSUES: [], Cmd.ENV_REPO: [], Cmd.ENV_LABELS: []} # selected environment elements
envHead = {Cmd.ENV_ISSUES: ['issue'], Cmd.ENV_REPO: '', Cmd.ENV_LABELS: ['label']} # environment headers

#
# Show command
def cmd_show():
  global dcmEnv, selEles, envEles, envHead

  if len(envEles[dcmEnv]) > 0:
    #for i,x in enumerate(envEles[dcmEnv]):
    #  if x in selEles[dcmEnv]:
    #    print(str(i) + ': ' + str(x) + ' *')
    #  else:
    #    print(str(i) + ': ' + str(x))
    mytable = []
    for i,x in enumerate(envEles[dcmEnv]):
      if isinstance(x, tuple):
        x_str = dcm_util.tuple_to_str(x)
      else:
        x_str = str(x)
      x_str = str(i) + (', *' if x in selEles[dcmEnv] else ', ') + ', ' + x_str
      mytable.append(x_str.split(', '))

    myheaders = ['num', 'sel']
    myheaders.extend(envHead[dcmEnv])
    print()
    print(tabulate(mytable, headers=myheaders, tablefmt='simple'))
    print()

#
# Select command
def cmd_select(par, withReset):
  global dcmEnv, selEles, envEles

  par = par.strip()
  if par == Cmd.PAR_ALL: 
    selEles[dcmEnv] = list(envEles[dcmEnv])
    print('all selected')
  else:
    if withReset:
      selEles[dcmEnv] = []

    for x in par.split():
      ele = envEles[dcmEnv][int(x)]
      if not (ele in selEles[dcmEnv]): 
        selEles[dcmEnv].append(ele)
        print(str(ele) + ' *')
  print()

#
# UnSelect command
def cmd_unselect(par):
  global dcmEnv, selEles, envEles

  par = par.strip()
  if par == Cmd.PAR_ALL:
    selEles[dcmEnv] = []
  else:
    for x in par.split():
      ele = envEles[dcmEnv][int(x)]
      selEles[dcmEnv].remove(ele)

#
# Scan command
def cmd_scan(repo):
  global dcmEnv, selEles, envEles
  repo.scan()
  repo.copy_issues_to_filtered()
  selEles[dcmEnv] = []
  cmd_show()

#
# Check for selected elements
def check_selected_elements(max = -1, ask_sure = False):
  global dcmEnv, selEles, envEles

  if len(selEles[dcmEnv]) < 1: 
    if len(envEles[dcmEnv]) == 1: 
      print('single element selected')
      selEles[dcmEnv].append(envEles[dcmEnv][0])
      return True

    print_error('no element selected')
    return False

  if max > 0 and len(selEles[dcmEnv]) > max:
    if ask_sure:
      return get_confirm()

    print_error('too many elements selected')
    return False

  return True
#
# Check first parameter
def check_1st_param(ws, errFlag):
  if ws[1] == '':
    if errFlag: print_error('parameter missing')
    return False

  return True

#
# print with color
def print_color(c, s, myend='x'):
  if myend == 'x':
    print(c + s + Style.RESET_ALL)
  else:
    print(c + s + Style.RESET_ALL, end=myend)

#
# print error
def print_error(s):
  print_color(Fore.RED, s)

#
# input with color
def input_split_color(c, s):
  print_color(c, s, '')
  return input().split()

#
# environment prompt
def env_prompt():
  global dcmEnv, selEles, envEles
  
  msg = dcmEnv + ' [' + str(len(selEles[dcmEnv])) + '/' + str(len(envEles[dcmEnv])) + ']# '
  if dcmEnv == Cmd.ENV_ISSUES:
    return input_split_color(Fore.YELLOW, msg)
  
  if dcmEnv == Cmd.ENV_LABELS:
    return input_split_color(Fore.CYAN, msg)
  
  return input(msg).split()

#
# get user confirm
def get_confirm():
  if input_split_color(Fore.RED, 'sure? (y/n): ')[0] == 'y': return True
  return False

#
# get input
def get_input(text, defValue):
  resValue = input(text + ' [def: ' + defValue + ', . to cancel]: ')
  if resValue == '.':
    return False, defValue

  if resValue == '': resValue = defValue
  if resValue == ' ': resValue = ''
  return True, resValue.strip()

#
# get labels
def get_labels(defValue):
  resValue = input('labels [def: ' + defValue + ', l to show labels, . to cancel]: ')
  if resValue == '.':
    return False, defValue

  if resValue == 'l':
    i = 0
    line = ''
    for x in repo.labels:
      if i >= 3:
        print_color(Fore.CYAN, line)
        line = ''
        
      if line == '':
        line = str(x)
      else:
        line = line + '\t' + str(x)
      i = i + 1

    if line != '':
      print_color(Fore.CYAN, line)

    return get_labels(defValue)

  if resValue == '': resValue = defValue
  if resValue == ' ': resValue = ''
  return True, resValue.strip()

#
# get repo entry input
def get_rentry_input(title, lang, labels, keywords):
  r, title = get_input('title', title)
  if not r: return False, title, lang, labels, keywords
  r, lang = get_input('language (it, en)', lang)
  if not r: return False, title, lang, labels, keywords
  #r, labels = get_input('labels', labels)
  r, labels = get_labels(labels)
  if not r: return False, title, lang, labels, keywords

  #r, keywords = get_input('keywords', keywords)
  #if not r: return False, title, lang, labels, keywords
  return True, title, lang, labels, keywords

#
# get filter input
def get_filter_input(kind, url, title, lang, labels, keywords):
  r, kind = get_input('kind', kind)
  if not r: return False, kind, url, title, lang, labels, keywords
  r, url = get_input('url', url)
  if not r: return False, kind, url, title, lang, labels, keywords
  r, title, lang, labels, keywords = get_rentry_input(title, lang, labels, keywords)
  if not r: return False, kind, url, title, lang, labels, keywords

  return True, kind, url, title, lang, labels, keywords

#
# resolve a scan issue with a function (f :: issue -> bool)
def resolve_issue(msg, f):
  global dcmEnv, selEles, envEles
  
  done_issues = []
  for issue in selEles[dcmEnv]:
    if f(issue):
      print(issue.url + msg)
      done_issues.append(issue)
  print()

  for issue in done_issues:
    repo.issues.remove(issue)
  selEles[dcmEnv] = []

#
# Add a bookmark to the DB
def cmd_add_bookmark(inp_values):
  r, url = get_input('url', '')
  if not r: return

  r, inp_values[Cmd.ITITLE], inp_values[Cmd.ILANG], inp_values[Cmd.ILABELS], inp_values[Cmd.IKEYWORDS] = get_rentry_input('', inp_values[Cmd.ILANG], inp_values[Cmd.ILABELS], inp_values[Cmd.IKEYWORDS])
  if not r: return
  if repo.add_bookmark_db(url, inp_values[Cmd.ITITLE], inp_values[Cmd.ILANG], inp_values[Cmd.ILABELS], inp_values[Cmd.IKEYWORDS]):
    print('url added')
  else:
    print_error('url already present!')

#
# Print help
def printHelp(par):
  
  if par == '':
    printHelp(Cmd.ENV_ISSUES)
    printHelp(Cmd.ENV_LABELS)
    printHelp(Cmd.ENV_REPO)
    return

  if par == Cmd.ENV_ISSUES:
    print('======= ' + par + ' =======')
    print(Cmd.CMD_HELP + ' [*]: print help message')
    print(Cmd.ISSUES_SCAN + ': scan the repository for new files or problems')
    print(Cmd.CMD_SHOW + ': show scanned files')
    print(Cmd.CMD_SELECT + ' <index1 index2 ...>|*: select scanned files')
    print()
    print(Cmd.ISSUES_ADD_FILE_DB + ' [<index>]: add file to the DB')
    print(Cmd.ISSUES_ADD_MUL_FILES_DB + ' [<index>]: add files to the DB')
    print(Cmd.ISSUES_DEL_MISSING_DB + ' [<index>]: remove missing DB entry')
    print(Cmd.ISSUES_IGNORE_FILE_DB + ' [<index>]: ignore file')
    print(Cmd.ISSUES_FIX_FILE_DB + ' [<index>]: pair missing DB entry with new file')
    print(Cmd.ISSUES_OPEN_FILE + ' [<index>]: open selected file')
    print(Cmd.ISSUES_ADD_BOOKMARK_DB + ': add a bookmark to the DB')
    print()
    return

  if par == Cmd.ENV_LABELS:
    print('======= ' + par + ' =======')
    print(Cmd.CMD_HELP + ' [*]: print help message')
    print(Cmd.CMD_SHOW + ': show labels')
    print(Cmd.CMD_SELECT + ' <index1 index2 ...>|*: select labels')
    print()
    print(Cmd.LABELS_DEL + ' [<index>]: delete a label')
    print(Cmd.LABELS_RENAME + ' <new name>: rename a label')
    print()
    return

  if par == Cmd.ENV_REPO:
    print('======= ' + par + ' =======')
    print(Cmd.CMD_HELP + ' [*]: print help message')
    print(Cmd.CMD_SHOW + ': show filtered files')
    print(Cmd.ISSUES_SCAN + ': scan the repository for new files or problems')
    print(Cmd.REPO_FAVORITE + '  [<index>]: show favorites/toggle favor on selected item')
    print(Cmd.CMD_SELECT + ' <index1 index2 ...>|*: select filtered files')
    print()
    print(Cmd.REPO_COLS + ' [<colums>|*]: show/change shown column')
    print(Cmd.REPO_RESET + ': reset applied filters')
    print(Cmd.REPO_WHERE + ': show where clause')
    print(Cmd.REPO_ORDER + ' [<column>]: show/change row order')
    print(Cmd.REPO_AND + ': sql and')
    print(Cmd.REPO_OR + ': sql or')
    print(Cmd.REPO_FILTER + ': filter UI')
    print(Cmd.REPO_ANY + ' <string1 string2 ...>: filter any item characterized with the all the items in the input string')
    print(Cmd.REPO_SEARCH + ' <string>: search for documents that contains the input string')
    print()
    print(Cmd.REPO_HTML + ' <filepath>: export selected items to html')
    print(Cmd.REPO_CSV + ' <filepath>: export selected items to csv')
    print()
    print(Cmd.REPO_S_OPEN + ' [<index>]: open selected file/url')
    print(Cmd.REPO_S_COPY + ' <filepath>: copy selected file')
    print(Cmd.REPO_S_COPY_DESK + ' [<index>]: copy selected file to desktop')
    print(Cmd.REPO_S_CLIP + ' [<index>]: copy selected item path/url to clipboard')
    print(Cmd.REPO_S_LABEL + ' [<index>]: toggle label on selected item')
    print(Cmd.REPO_S_TITLE + ' [<index>]: change title of selected file')
    print(Cmd.REPO_S_DEL + ' [<index>]: remove selected item from DB')
    print(Cmd.REPO_S_INFO + ' [<index>]: show extra info on selected item')
    print()
    print(Cmd.ISSUES_ADD_FILE_DB + ' [<index>]: add file to the DB')
    print(Cmd.ISSUES_ADD_MUL_FILES_DB + ' [<index>]: add files to the DB')
    print(Cmd.ISSUES_DEL_MISSING_DB + ' [<index>]: remove missing DB entry')
    print(Cmd.ISSUES_IGNORE_FILE_DB + ' [<index>]: ignore file')
    print(Cmd.ISSUES_FIX_FILE_DB + ' [<index>]: pair missing DB entry with new file')
    print(Cmd.ISSUES_ADD_BOOKMARK_DB + ': add a bookmark to the DB')
    print()
    return

  print_error('not found: ' + par)

#
# Print help
def manageCmd(repo, inp_values, filters, ws):
  global dcmEnv, selEles, envEles, envHead

  # ---- environment common commands
  if ws[0] == Cmd.CMD_SHOW or ws[0] == 's': 
    cmd_show()
    return

  if ws[0] == Cmd.CMD_SELECT:
    if not check_1st_param(ws, True): return

    cmd_select(' '.join(ws[1:]), False)
    return

  if ws[0] == Cmd.CMD_UNSELECT:
    if not check_1st_param(ws, True): return

    cmd_unselect(' '.join(ws[1:]))
    return

  # ------------- issues
  #MTB [18/07/2018]: issues commands are now usable in the repo environment
  #if dcmEnv == Cmd.ENV_ISSUES:
  if dcmEnv == Cmd.ENV_ISSUES or dcmEnv == Cmd.ENV_REPO:
    if ws[0] == Cmd.ISSUES_SCAN:
      cmd_scan(repo)
      return

    if ws[0] == Cmd.ISSUES_ADD_FILE_DB:
      if envEles[dcmEnv] != repo.issues:
        print_error('issues environment required');
        return

      if check_1st_param(ws, False): cmd_select(' '.join(ws[1:]), True)
      if not check_selected_elements(1): return
      
      issue = selEles[dcmEnv][0]
      if issue.kind != dcm_issue.RepoIssueKind.NEW: 
        print_error('this is not a NEW file');
        return

      title = os.path.splitext(issue.url)[0].replace('_', ' ')
      r, inp_values[Cmd.ITITLE], inp_values[Cmd.ILANG], inp_values[Cmd.ILABELS], inp_values[Cmd.IKEYWORDS] = get_rentry_input(title, inp_values[Cmd.ILANG], inp_values[Cmd.ILABELS], inp_values[Cmd.IKEYWORDS])
      if not r: return

      resolve_issue(' added', lambda issue: repo.add_doc_db(issue, inp_values[Cmd.ITITLE], inp_values[Cmd.ILANG], inp_values[Cmd.ILABELS], inp_values[Cmd.IKEYWORDS]))
      return

    if ws[0] == Cmd.ISSUES_ADD_MUL_FILES_DB:
      if envEles[dcmEnv] != repo.issues:
        print_error('issues environment required');
        return

      if check_1st_param(ws, False): cmd_select(' '.join(ws[1:]), True)
      if not check_selected_elements(): return
      
      r, inp_values[Cmd.ITITLE], inp_values[Cmd.ILANG], inp_values[Cmd.ILABELS], inp_values[Cmd.IKEYWORDS] = get_rentry_input('---', inp_values[Cmd.ILANG], inp_values[Cmd.ILABELS], inp_values[Cmd.IKEYWORDS])
      if not r: return

      resolve_issue(' added', lambda issue: repo.add_doc_db(issue, os.path.splitext(issue.url)[0].replace('_', ' '), inp_values[Cmd.ILANG], inp_values[Cmd.ILABELS], inp_values[Cmd.IKEYWORDS]))
      return

    if ws[0] == Cmd.ISSUES_DEL_MISSING_DB:
      if envEles[dcmEnv] != repo.issues:
        print_error('issues environment required');
        return

      if check_1st_param(ws, False): cmd_select(' '.join(ws[1:]), True)
      if not check_selected_elements(): return
      if not get_confirm(): return

      resolve_issue(' removed', lambda issue: repo.remove_missing_entry_db(issue))
      return

    if ws[0] == Cmd.ISSUES_IGNORE_FILE_DB:
      if envEles[dcmEnv] != repo.issues:
        print_error('issues environment required');
        return

      if not check_selected_elements(): return
      if not get_confirm(): return

      resolve_issue(' ignored', lambda issue: repo.ignore_doc_db(issue))
      return

    if ws[0] == Cmd.ISSUES_FIX_FILE_DB:
      if envEles[dcmEnv] != repo.issues:
        print_error('issues environment required');
        return

      if check_1st_param(ws, False): cmd_select(' '.join(ws[1:]), True)
      if not check_selected_elements(2): return
      if len(selEles[dcmEnv]) < 2: 
        print_error('not enough elements selected')
        return
      
      if not repo.fix_missing_db(selEles[dcmEnv][0], selEles[dcmEnv][1]):
        print_error('error!')
        return

      repo.issues.remove(selEles[dcmEnv][0])
      repo.issues.remove(selEles[dcmEnv][1])
      selEles[dcmEnv] = []
      print('fixed')
      return

    #if ws[0] == Cmd.ISSUES_OPEN_FILE:
    #  if check_1st_param(ws, False): cmd_select(' '.join(ws[1:]), True)
    #  if not check_selected_elements(3, True): return
    #  for issue in selEles[dcmEnv]:
    #    os.startfile(os.path.join(repo_dir_path, issue.url))
    #  return

    if ws[0] == Cmd.ISSUES_ADD_BOOKMARK_DB:
      cmd_add_bookmark(inp_values)
      return

  # ------------- repo
  if dcmEnv == Cmd.ENV_REPO:
    if ws[0] == Cmd.REPO_COLS:
      if ws[1] != '': 
        if ws[1] == '*': 
          repo.active_sql_cols = repo.COLS_ALL
        else:
          repo.active_sql_cols = ' '.join(ws[1:])
        repo.update_filtered()
      print('all columns: ' + repo.COLS_ALL)
      print('shown columns: ' + repo.active_sql_cols)
      print()
      return

    if ws[0] == Cmd.REPO_RESET or ws[0] == 'r':
      print('filter reset')
      repo.set_def_filter()
      repo.update_filtered()
      selEles[dcmEnv] = []
      return

    if ws[0] == Cmd.REPO_WHERE:
      print(repo.where_clause.strip())
      print()
      return

    if ws[0] == Cmd.REPO_ORDER:
      if ws[1] != '': 
        repo.orderby_clause = ' ORDER BY ' + ws[1];
        repo.update_filtered()
        #selEles[dcmEnv] = []
        cmd_show()
      else:
        print(repo.orderby_clause.strip())
        print()
      return

    if ws[0] == Cmd.REPO_AND:
      if not check_1st_param(ws, True): return

      repo.where_clause = repo.where_clause + ' AND ' + ' '.join(ws[1:])
      repo.update_filtered()
      selEles[dcmEnv] = []
      return

    if ws[0] == Cmd.REPO_OR:
      if not check_1st_param(ws, True): return

      repo.where_clause = repo.where_clause + ' OR ' + ' '.join(ws[1:])
      repo.update_filtered()
      selEles[dcmEnv] = []
      return

    if ws[0] == Cmd.REPO_FILTER:
      r, case_sensitive = get_input('case sensitive', 'n')
      if not r: return

      r, filters[Cmd.IKIND], filters[Cmd.IURL], filters[Cmd.ITITLE], filters[Cmd.ILANG], filters[Cmd.ILABELS], filters[Cmd.IKEYWORDS] = get_filter_input(filters[Cmd.IKIND], filters[Cmd.IURL], filters[Cmd.ITITLE], filters[Cmd.ILANG], filters[Cmd.ILABELS], filters[Cmd.IKEYWORDS])
      if not r: return
      
      filters = list(map(lambda x: x.strip(), filters))

      repo.set_andor_filter(True, case_sensitive == 'y', filters[Cmd.IKIND], filters[Cmd.IURL], filters[Cmd.ITITLE], filters[Cmd.ILANG], filters[Cmd.ILABELS], filters[Cmd.IKEYWORDS], True)
      selEles[dcmEnv] = []
      cmd_show()
      return

    if ws[0] == Cmd.REPO_ANY:
      if not check_1st_param(ws, True): return
      doReset = True
      for w in ws[1:]:
        search_str = '%' + w + '%'
        repo.set_andor_filter(doReset, False, '', search_str, search_str, '', search_str, search_str, False)
        doReset = False

      selEles[dcmEnv] = []
      cmd_show()
      return

    if ws[0] == Cmd.REPO_SEARCH:
      if not check_1st_param(ws, True): return
      repo.search_string(ws[1], True)
      selEles[dcmEnv] = []
      cmd_show()
      return

    if ws[0] == Cmd.REPO_HTML:
      if not check_1st_param(ws, True): return
      if not check_selected_elements(): return

      rowids = list(map(lambda se: repo.get_rowid(se), selEles[dcmEnv]))
      repo.export_to_csv_html(rowids, ws[1], False)
      print('html saved')
      return

    if ws[0] == Cmd.REPO_CSV:
      if not check_1st_param(ws, True): return
      if not check_selected_elements(): return

      rowids = list(map(lambda se: repo.get_rowid(se), selEles[dcmEnv]))
      repo.export_to_csv_html(rowids, ws[1], True)
      print('csv saved')
      return

    if ws[0] == Cmd.REPO_FAVORITE:
      if check_1st_param(ws, False): 
        cmd_select(' '.join(ws[1:]), True)
        if not check_selected_elements(3, True): return
        for se in selEles[dcmEnv]:
          row_id = repo.get_rowid(se)
          title = repo.get_title(row_id)
          if repo.toggle_favorite(row_id):
            print(title + ' -- added to favorite')
          else:
            print(title + ' -- removed from favorite')
      else:
        repo.set_filter_favorite()
        selEles[dcmEnv] = []
        cmd_show()
      return

    if ws[0] == Cmd.REPO_S_OPEN:
      if check_1st_param(ws, False): cmd_select(' '.join(ws[1:]), True)
      if not check_selected_elements(3, True): return
      
      if selEles[dcmEnv] == repo.issues:
        for se in selEles[dcmEnv]:
          os.startfile(os.path.join(repo_dir_path, se.url))
      else:
        for se in selEles[dcmEnv]:
          repo.open_item(repo.get_rowid(se))
      return

    if ws[0] == Cmd.REPO_S_COPY_DESK:
      if check_1st_param(ws, False): cmd_select(' '.join(ws[1:]), True)
      ws[0] = Cmd.REPO_S_COPY
      ws[1] = os.path.join(os.environ["HOMEDRIVE"], os.environ["HOMEPATH"], "Desktop")

    if ws[0] == Cmd.REPO_S_COPY:
      if not check_1st_param(ws, True): return
      if not check_selected_elements(3, True): return

      for se in selEles[dcmEnv]:
        rowid = repo.get_rowid(se)
        if repo.get_kind(rowid) != dcm_repo.ResourceKind.DOC: continue
        url = repo.get_url(rowid)
        if dcm_util.safe_copy(url, ws[1]):
          print(url + ' --> ' + ws[1])
        else:
          print_error(url + ' --- not copied')
      return

    if ws[0] == Cmd.REPO_S_CLIP:
      if check_1st_param(ws, False): cmd_select(' '.join(ws[1:]), True)
      if not check_selected_elements(): return

      urls = []
      for se in selEles[dcmEnv]:
        urls.append(repo.get_url(repo.get_rowid(se)))
      pyperclip.copy('\n'.join(urls))
      return

    if ws[0] == Cmd.REPO_S_LABEL:
      if check_1st_param(ws, False): cmd_select(' '.join(ws[1:]), True)
      if not check_selected_elements(3, True): return

      r, label = get_input('label', '')
      if not r: return

      for se in selEles[dcmEnv]:
        rowid = repo.get_rowid(se)
        title = repo.get_title(rowid)
        if repo.toggle_label(rowid, label):
          print(title + ' -- label added')
        else:
          print(title + ' -- label removed')
      selEles[dcmEnv] = []
      return
      
    if ws[0] == Cmd.REPO_S_TITLE:
      if check_1st_param(ws, False): cmd_select(' '.join(ws[1:]), True)
      if not check_selected_elements(1): return
      r, title = get_input('title', repo.get_title(repo.get_rowid(selEles[dcmEnv][0])))
      if not r: return

      repo.change_title(repo.get_rowid(selEles[dcmEnv][0]), title)
      selEles[dcmEnv] = []
      return

    if ws[0] == Cmd.REPO_S_DEL:
      if check_1st_param(ws, False): cmd_select(' '.join(ws[1:]), True)
      if not check_selected_elements(1): return
      if not get_confirm(): return
      rowid = repo.get_rowid(selEles[dcmEnv][0])
      if repo.get_kind(rowid) == dcm_repo.ResourceKind.DOC:
        if input('the file will be deleted too, continue? (y/n): ') != 'y': return
      repo.remove_entry_db_file(rowid)
      selEles[dcmEnv] = []
      return

    if ws[0] == Cmd.REPO_S_INFO:
      if check_1st_param(ws, False): cmd_select(' '.join(ws[1:]), True)
      if not check_selected_elements(): return

      for se in selEles[dcmEnv]:
        repo.print_extra_info(repo.get_rowid(se))
      return

  # ------------- labels
  if dcmEnv == Cmd.ENV_LABELS:
    if ws[0] == Cmd.LABELS_DEL:
      if check_1st_param(ws, False): cmd_select(' '.join(ws[1:]), True)
      if not check_selected_elements(): return
      if not get_confirm(): return

      for l in selEles[dcmEnv]:
        if repo.remove_label_db(l):
          print(l + ' removed')
      return

    if ws[0] == Cmd.LABELS_RENAME:
      if not check_1st_param(ws, True): return
      if not check_selected_elements(1): return
      if not get_confirm(): return

      for l in selEles[dcmEnv]:
        if repo.rename_label_db(l, ws[1]):
          print(l + ' renamed in ' + ws[1])
      return

  # unknown command
  print_error('unknown or incorrect command')

#
# Main
#
if __name__ == '__main__':
  if len(sys.argv) < 4:
    print('usage: ' + sys.argv[0] + ' <repo user> <repo csv file path> <repo dir path>')
    exit()

  print('========================')
  print('======= dcm v0.3 =======')
  print('========================')
  repo_user = sys.argv[1]
  repo_csv_path = sys.argv[2]
  repo_dir_path = sys.argv[3]
  #repo_html_path = sys.argv[4]

  t0 = time.time()

  # colorama init
  init()
  
  # RepoManager
  repo = dcm_repo.RepoManager(repo_user, repo_csv_path, repo_dir_path)
  repo.open()
  
  t1 = time.time()
  total_time = t1-t0
  print('repo init time: ' + str(round(total_time / 1000, 1)))

  envEles[Cmd.ENV_ISSUES] = repo.issues
  envEles[Cmd.ENV_REPO] = repo.filtered
  envEles[Cmd.ENV_LABELS] = repo.labels
  envHead[Cmd.ENV_REPO] = repo.active_cols

  inp_values = ['', '', '', 'en', '', ''] #vedi variabili Cmd.I
  filters = ['', '', '', '', '', ''] #vedi variabili Cmd.I

  # initial scan
  t0 = time.time()

  repo.scan()
  
  t1 = time.time()
  total_time = t1-t0
  print('repo scan time: ' + str(round(total_time / 1000, 1)))

  if len(repo.issues) > 0:
    ws = input_split_color(Fore.RED, 'there are issues to fix (' + str(len(repo.issues)) + '), proceed? (y/n) ')
    if len(ws) >0 and ws[0] == 'y':
      #dcmEnv = Cmd.ENV_ISSUES
      #cmd_show()
      cmd_scan(repo)

  #--- shell main loop
  dcmEnvOld = ''
  while(True):
    ws = env_prompt()
    
    if len(ws) < 1: continue
    if len(ws) < 3:
      for i in range(0, 3 - len(ws)): ws.append('')

    try: 
      # ---- basic
      if ws[0] == 'q' or ws[0] == 'exit' or ws[0] == 'quit': break
      if ws[0] == 'h' or ws[0] == '?' or ws[0] == 'help': 
        if ws[1] == Cmd.PAR_ALL: printHelp('')
        else: printHelp(dcmEnv)
        continue

      # ---- environment change (NB: per ora non previsto il cambio temporaneo dell'environment)
      if ws[0] in [Cmd.ENV_ISSUES, Cmd.ENV_REPO, Cmd.ENV_LABELS]:
        if ws[1] == '':
          dcmEnv = ws[0]
          selEle = 0
          continue
        else:
          dcmEnvOld = dcmEnv
          dcmEnv = ws.pop(0)
          manageCmd(repo, inp_values, filters, ws)

          dcmEnv = dcmEnvOld
          continue

      manageCmd(repo, inp_values, filters, ws)
    except Exception as ex:
      print_error('something went wrong!!!!')
      traceback.print_exc()
  
  #--- end
  repo.close()
  print('Bye bye')
