from os import environ

from airtable import Airtable as AirtableInit, API_LIMIT

from constants import DEBUG_MODE


class Airtable(AirtableInit):
  def __init__(self, tableName):
    if tableName == "Participants":
      self._table = "Seyhan's testing group" if DEBUG_MODE else "Members"
    else:
      self._table = tableName

    super().__init__(
      environ.get('AIRTABLE_LINKEDIN_TABLE'),
      self._table,
      environ.get('AIRTABLE_KEY')
    )

  def delete_all(self):
    if input("You sure?"): ##############
      return
    self.batch_delete([record['id'] for record in self.get_all()])

  def update_all(self, fields):
    for row in self.get_all():
  		self.update(row['id'], fields)
  		time_sleep(API_LIMIT)



def addPairsToAirtable(pairs):
	airtablePairs = Airtable('Emails')
	# insert pairs (formatted into strings)
	pairsJSON = [
		{
			"ID" : row["ID"],
			"Profiles" : ','.join(str(i) for i in row["Profiles"]),
			"Profiles Assigned" : ','.join(str(i) for i in row["Profiles Assigned"]),
			"Timestamp" : row["Timestamp"]
		} for row in pairs
	]
	airtablePairs.batch_insert(pairsJSON)

"""
get_all

batch_delete
batch_insert

match

update_by_field("ID",)

"""


airtable = Airtable("Participants")
print(airtable.batch_update)
