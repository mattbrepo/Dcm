
#
# RepoIssue.kind possible values
class RepoIssueKind:
  NEW = 'new'
  MISSING = 'missing'

#
# An issue of the repository
class RepoIssue():

  def __init__(self, kind, url, rowid):
    self.kind = kind
    self.url = url
    self.rowid = rowid
    
  def __str__(self):
    if self.kind == RepoIssueKind.NEW:
      return self.url + ' -- NEW'
    else:
      return self.url + ' -- MISSING'
