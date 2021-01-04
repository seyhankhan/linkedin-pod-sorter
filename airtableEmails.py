from os import environ

from airtable import Airtable
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

################################ CALCULATE PAIRS ###############################


def calculateProfilePairs():
	airtableParticipants = Airtable(environ.get('AIRTABLE_TABLE'), 'Participants', environ.get('AIRTABLE_KEY'))
	participants = airtableParticipants.get_all(filterByFormula="NOT({Opted In}=Blank())")
	numParticipants = len(participants)

	shuffle(participants)

	MAX_PROFILES_PER_PERSON = 14
	# range of numbers from 1 to max profiles per person
  # 1,2,3,4,5,6,7,8,9,10,11,12,13,14
	profilePairIndices = range(1, min(MAX_PROFILES_PER_PERSON, numParticipants - 1) + 1)

	pairs = []
	# for each participant
	for participantIndex in range(numParticipants):
		pairs.append(
			{
				"ID": participants[participantIndex]['fields']["ID"],
				"Profiles": [
					participants[(participantIndex + i) % numParticipants]['fields']["ID"] for i in profilePairIndices
				]
			}
		)
	return pairs

def addPairsToAirtable(pairs):
	airtablePairs = Airtable(environ.get('AIRTABLE_TABLE'), 'Pairs', environ.get('AIRTABLE_KEY'))
	# clear every row from 'Pairs' table
	airtablePairs.batch_delete([record['id'] for record in airtablePairs.get_all()])
	# insert pairs (formatted into strings)
	pairsJSON = [
		{
			"ID" : str(row["ID"]),
			"Profiles" : ','.join(str(i) for i in row["Profiles"])
		} for row in pairs
	]
	airtablePairs.batch_insert(pairsJSON)

##################################### EMAIL ####################################

def CreateEmail(name, formLink, week, peopleToCommentOn, peopleThatWillComment):
	subject = 'Your LinkedIn profiles to interact with | '+week+' | LinkedIn Pod Sorter'
	f"""
Hey {name},

Feedback form for this week: {feedbackFormURL}

Which day would you like to receive next weeks email?
(Loved this post | Not easy to comment on | Post missing)
(thoughtful | Used hashtags or tagged name | Comment missing)



Here are your 4 profiles for this week of 21 - 25 Dec:
- Steve Johnson


These 4 people will interact with your posts:
- Billy Bobinson


	"""


def sendEmail(message):
	try:
		sg = SendGridAPIClient(environ.get('SENDGRID_KEY'))
		response = sg.send(message)
		print('Status Code:', response.status_code)
		print('Body:', response.body)
		print('Headers:', response.headers)
		return ''
	except Exception as e:
		print(e)
		return 'Error'


def sendFirstBatchOfWeeklyEmails(pairs):
	airtableParticipants = Airtable(environ.get('AIRTABLE_TABLE'), 'Participants', environ.get('AIRTABLE_KEY'))
	# get list of participants that are currently opted in
	participantsRAW = airtableParticipants.get_all(filterByFormula="NOT({Opted In}=Blank())")
	participants = {
		record['fields']['ID'] : record['fields'] for record in participantsRAW
	}

	# create each email
	messages = []
	# for each person in the table
	for pair in pairs:
		# record of receiver participant who is being SENT email
		receiverRecord = participants[pair["ID"]]
		# make a list with each participant ID's record
		# list of participants' records that receiver participant has to interact with
		emailList = [
			participants[id] for id in pair["Profiles"]
		]

		messages.append(
			Mail(
		    from_email=environ.get('FROM_EMAIL'),
		    to_emails=receiverRecord['Email'],
		    subject='Your LinkedIn profiles for this week | LinkedIn Pod Sorter',
		    html_content=createEmailHTML(
					receiverRecord['Name'],
					utf8_to_base64(receiverRecord["Email"]),
					emailList
				)
	  	)
		)

	# now send each email
	# if error occurs, output & end the function
	for message in messages:
		if sendEmail(message) == 'Error':
			return

	# email all non participants asking to confirm participation for next week
	nonparticipants = airtableParticipants.get_all(filterByFormula="{Opted In}=Blank()")
	for nonParticipant in nonparticipants:
		errorOccured = sendEmail(Mail(
			from_email=environ.get('FROM_EMAIL'),
			to_emails=nonParticipant['fields']['Email'],
			subject='Are you participating next week? | LinkedIn Pod Sorter',
			html_content=createEmailHTML(nonParticipant['fields']['Name'], utf8_to_base64(nonParticipant['fields']["Email"]))
		))
		if errorOccured == "Error":
			return

def sendSecondBatchOfWeeklyEmails(pairs):
	# get list of remaining participants
	airtablePairs = Airtable(environ.get('AIRTABLE_TABLE'), 'Pairs', environ.get('AIRTABLE_KEY'))
	pairs = airtablePairs.get_all()

	airtableParticipants = Airtable(environ.get('AIRTABLE_TABLE'), 'Participants', environ.get('AIRTABLE_KEY'))
	# get list of participants that are currently opted in
	participantsRAW = airtableParticipants.get_all(filterByFormula="NOT({Opted In}=Blank())")
	participants = {
		record['fields']['ID'] : record['fields'] for record in participantsRAW
	}

	# create each email
	messages = []
	# for each person in the table
	for pair in pairs:
		# record of receiver participant who is being SENT email
		receiverRecord = participants[pair["ID"]]
		# make a list with each participant ID's record
		# list of participants' records that receiver participant has to interact with
		emailList = [
			participants[id] for id in pair["Profiles"]
		]

		messages.append(
			Mail(
		    from_email=environ.get('FROM_EMAIL'),
		    to_emails=receiverRecord['Email'],
		    subject='Your LinkedIn profiles for this week | LinkedIn Pod Sorter',
		    html_content=createEmailHTML(
					receiverRecord['Name'],
					utf8_to_base64(receiverRecord["Email"]),
					emailList
				)
	  	)
		)

	# now send each email
	# if error occurs, output & end the function
	for message in messages:
		if sendEmail(message) == 'Error':
			return

	# email all non participants asking to confirm participation for next week
	nonparticipants = airtableParticipants.get_all(filterByFormula="{Opted In}=Blank()")
	for nonParticipant in nonparticipants:
		errorOccured = sendEmail(Mail(
			from_email=environ.get('FROM_EMAIL'),
			to_emails=nonParticipant['fields']['Email'],
			subject='Are you participating next week? | LinkedIn Pod Sorter',
			html_content=createEmailHTML(nonParticipant['fields']['Name'], utf8_to_base64(nonParticipant['fields']["Email"]))
		))
		if errorOccured == "Error":
			return
