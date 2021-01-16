from os import environ
from time import sleep as time_sleep

from airtable import Airtable

from constants import *
from emails import *

"""
make these run 19:30, the night before!!
make sunday emails send at local time zone
"""

currentDate = getCurrentDatetime()

airtableParticipants = Airtable("Participants")
participants = {
	row['fields']['ID'] : row['fields'] for row in airtableParticipants.get_all(
		fields=[
			 'ID','Name','Email','LinkedIn Profile','Day Preference','Time Zone','Group'
		]
	)
}
airtablePairs = Airtable('Emails')


#################################### SUNDAY ####################################


# Runs Sat, at 1830
if currentDate.weekday() == 5:
	# clear everyone's day choice from last Mon-Fri
	airtableParticipants.update_all({"Day Preference": []})

	# clear every row from 'Emails' table
	airtablePairs.delete_all()

	sendTimestamp = calculateEmailTimestamp('Sunday', 'UTC')
	emails = createCommitEmails(participants, sendTimestamp)
	for email in emails:
		print(sendEmail(email))


############################### MONDAY to FRIDAY ###############################


# Runs Sun-Thu, at 1830
if (currentDate.weekday() + 1) % 7 < 5:
	groups = {}
	for participant in participants.values():
		# if participant picked no days, skip em
		if "Day Preference" not in participant:
			continue
		# if today was NOT one of this participant's choices, skip em
		if currentDate.strftime("%A") not in participant['Day Preference']:
			continue

		if participant['Group'] in groups:
			groups[participant['Group']].append(participant)
		else:
			groups[participant['Group']] = [participant]

	pairs = generateAllPairsAndTimestamps(groups, currentDate.strftime("%A"))

	addPairsToAirtable(pairs)

	emails = createProfilesEmail(participants, pairs)

	# now send each email
	# if error occurs, output ERROR
	for email in emails:
		print(sendEmail(email))


# First email is sent Sunday, 18:30 UTC (New Zealand)
# Last email is sent Friday, 17:30 UTC (Hawaii)
