from random import shuffle

from airtables import Airtable
from constants import MAX_PROFILES_PER_PERSON
from datetimes import calculateEmailTimestamp, getCurrentDatetime, getWeekToCommitToRange
from emails import *

"""
make these run 18:30, the night before!!
make sunday emails send at local time zone
"""

currentDate = getCurrentDatetime().date()
# if today is sat, nothing to do, just exit program
if currentDate.weekday() == 5:
	exit()

airtablePairs = Airtable('Emails')
airtableParticipants = Airtable("Participants")
participants = {
	row['fields']['ID'] : row['fields'] for row in airtableParticipants.get_all(
		fields=[
			 'ID','Name','Email','LinkedIn Profile','Day Preference','Time Zone','Group'
		]
	)
}


#################################### SUNDAY ####################################


# Runs Sun, at 0000
if currentDate.weekday() == 6:
	# clear everyone's day choice from last Mon-Fri
	airtableParticipants.update_all({"Day Preference": []})

	# clear every row from 'Emails' table
	airtablePairs.delete_all()

	emails = createCommitEmails(
		participants,
		calculateEmailTimestamp(currentDate, 'UTC'),
		getWeekToCommitToRange()
	)
	
	sendEmails(emails)


############################### MONDAY to FRIDAY ###############################


# Runs Mon-Thu, at 0000
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


	pairsRows = []
	for group in groups:
		numParticipants = len(groups[group])
		shuffle(groups[group])

		# range of numbers from 1 to max profiles per person
		# 1,2,3,4,5,6,7,8,9,10,11,12,13,14,15
		profilePairIndices = range(1, min(MAX_PROFILES_PER_PERSON, numParticipants - 1) + 1)

		pairs = []
		# for each participant
		for participantIndex in range(numParticipants):
			pairs.append(
				{
					"ID": groups[group][participantIndex]["ID"],
					"Profiles": [
						groups[group][(participantIndex + i) % numParticipants]["ID"] for i in profilePairIndices
					],
					"Profiles Assigned": [
						groups[group][(participantIndex - i) % numParticipants]["ID"] for i in profilePairIndices
					],
					"Timestamp": calculateEmailTimestamp(
						currentDate,
						groups[group][participantIndex]["Time Zone"]
					)
				}
			)
		pairsRows.extend(pairs)

	# add pairs to Emails table (formatted to strings)
	airtablePairs.batch_insert([
		{
			"ID" : row["ID"],
			"Profiles" : ','.join(str(i) for i in row["Profiles"]),
			"Profiles Assigned" : ','.join(str(i) for i in row["Profiles Assigned"]),
			"Timestamp" : row["Timestamp"]
		} for row in pairs
	])

	emails = createProfilesEmail(
		participants,
		pairs,
		currentDate.strftime("%-d %b")
	)

	# now send each email
	# if error occurs, output ERROR
	sendEmails(emails)


# First email is sent Sunday, 18:30 UTC (New Zealand)
# Last email is sent Friday, 17:30 UTC (Hawaii)
