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


def createEmailHTML(name, userHash, pairs=None):
	if pairs:
		template = f"""
			<!doctype html>
			<html>
				<head>
					<meta charset="utf-8">
					<meta name="author" content="Seyhan Van Khan">
					<meta name="description" property="og:description" content="Your list of new LinkedIn profiles is here!">
					<title>Pod Sorter for LinkedIn</title>
					<style>
						body {{
							color: black;
						}}
					</style>
				</head>
				<body>
					Hey {name},
					<br>
					<br>
					<a href="https://linkedin-pod-sorter.herokuapp.com/topup?user={userHash}" target="_blank">Click here to confirm your participation for next week</a>
					<br>
					<b>Here are this weeks {len(pairs)} LinkedIn profiles.</b>
					<ul>
		"""
		for pair in pairs:
			template += f"<li><a href='{pair['LinkedIn Profile']}' target='_blank'>{pair['Name']}</a></li>"

		template += f"""
					</ul>
					<br>
					Regards,<br>
					LinkedIn Pod Sorter
				</body>
			</html>
		"""

	else:
		template = f"""
			<html>
				<head>
					<meta charset="utf-8">
					<meta name="author" content="Seyhan Van Khan">
					<meta name="description" property="og:description" content="Are you participating next week?">
					<title>Pod Sorter for LinkedIn</title>
					<style>
						body {{
							color: black;
						}}
					</style>
				</head>
				<body>
					Hey {name},
					<br>
					<br>
					<a href="https://linkedin-pod-sorter.herokuapp.com/topup?user={userHash}" target="_blank">Click here to confirm your participation for next week</a>
					<br>
					Regards,<br>
					LinkedIn Pod Sorter
				</body>
			</html>
		"""
	return template


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
