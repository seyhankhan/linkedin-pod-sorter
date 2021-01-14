from os import environ

from airtable import Airtable

from emails import DAYS, clearAllDayPreferences, getTodaysDate, createCommitEmails, createProfilesEmail, sendEmail, generateAllPairsAndTimestamps, addPairsToAirtable

"""
make these run 19:30, the night before!!
make sunday emails send at local time zone
"""

DEBUG_MODE = True
PEOPLE_TABLE = "Seyhan's testing group" if DEBUG_MODE else 'Members'

currentDate = getCurrentDatetime()

airtableParticipants = Airtable(environ.get('AIRTABLE_LINKEDIN_TABLE'), PEOPLE_TABLE, environ.get('AIRTABLE_KEY'))
participants = {
	row['fields']['ID'] : row['fields'] for row in airtableParticipants.get_all(
		fields=[
			 'ID','Name','Email','LinkedIn Profile','Day Preference','Time Zone','Group'
		]
	)
}


#################################### SUNDAY ####################################


# Runs every Sunday, 07:30 UTC
if currentDate.weekday() == DAYS.index('Sunday'):
	# clear everyone's day choice from last Mon-Fri
	clearAllDayPreferences(airtableParticipants)

	emails = createCommitEmails(participants)
	for email in emails:
		print(sendEmail(email))


############################### MONDAY to FRIDAY ###############################


# Runs Mon-Fri, at 07:30 UTC			(should be running 1930 day before)
if currentDate.weekday() < 5:
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


# First email is sent Sunday, 19:30 UTC (New Zealand)
# Last email is sent Friday, 17:30 UTC (Hawaii)
