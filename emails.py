from base64 import b64decode, b64encode
from datetime import datetime, timedelta, date, time
from os import environ
from pytz import UTC
from random import shuffle
from time import sleep as time_sleep

from airtable import Airtable
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, SendAt


################################## ID HASHING ##################################


def base64_to_utf8(letters):
	letters += "=" * (4 - len(letters) % 4)
	return b64decode(letters.encode()).decode()

def utf8_to_base64(letters):
	return b64encode(letters.encode("utf-8")).decode("utf-8").replace("=","")

# takes integer ID, convert to string hash
def hashID(id):
	return utf8_to_base64(str(id) + "-podsorter")

# takes string hash, convert to integer ID
def unhashID(idHash):
	return int(base64_to_utf8(idHash).split("-")[0])


################################ CALCULATE PAIRS ###############################


def calculateProfilePairs(group, airtableParticipants):
	participants = airtableParticipants.get_all(
		filterByFormula='AND({Group}="'+group+'", NOT({Opted In}=Blank()))'
	)
	numParticipants = len(participants)

	shuffle(participants)

	MAX_PROFILES_PER_PERSON = 5#14
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
				],
				"Profiles Assigned": [
					participants[(participantIndex - i) % numParticipants]['fields']["ID"] for i in profilePairIndices
				]
			}
		)
	return pairs


def addPairsToAirtable(pairs):
	airtablePairs = Airtable(environ.get('AIRTABLE_LINKEDIN_TABLE'), 'Pairs', environ.get('AIRTABLE_KEY'))
	# clear every row from 'Pairs' table
	airtablePairs.batch_delete([record['id'] for record in airtablePairs.get_all()])
	# insert pairs (formatted into strings)
	pairsJSON = [
		{
			"ID" : row["ID"],
			"Profiles" : ','.join(str(i) for i in row["Profiles"]),
			"Profiles Assigned" : ','.join(str(i) for i in row["Profiles Assigned"])
		} for row in pairs
	]
	airtablePairs.batch_insert(pairsJSON)


def optOutEveryone(airtableTable):
	for row in airtableTable.get_all(filterByFormula="NOT({Opted In}=Blank())"):
		airtableTable.update(row['id'], {"Opted In" : False})
		time_sleep(0.2)


##################################### TIME #####################################


EMAIL_SEND_LOCALTIME = time(7, 30, tzinfo=UTC)

def timestamp(day, timeDifferenceFromUTC):
	days = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
	today = date.today()

	# go back to the last monday
	# add a week if it's Sat or Sun
	# add days to make it the Day Preference
	nextWeekday = today \
		+ timedelta(days=days.index(day)-today.weekday(), weeks=int(today.weekday() > 4))

	datetimeToSendLocal = datetime.combine(nextWeekday, EMAIL_SEND_LOCALTIME)

	return int(
		(datetimeToSendLocal - timedelta(hours=timeDifferenceFromUTC)).timestamp()
	)

# 29 Dec - 2 Jan
def getWeekString():
	today = date.today()
	# if today is SAT OR SUN, it made it the previous monday when it should be the next
	# 	add 7 days to the date
	monday = today + timedelta(
		days = 7 * int(today.weekday() > 4) - today.weekday()
	)
	friday = monday + timedelta(days=4)

	# Add monday's month if different to friday's
	extraMonth = " %b" if monday.month != friday.month else ""

	return datetime.strftime(monday, "%-d" + extraMonth) + " - " + datetime.strftime(friday, "%-d %b")


##################################### EMAIL ####################################


def Email(to, subject, html, timestamp=None):
	email = Mail(
    from_email=environ.get('FROM_EMAIL'),
    to_emails=to,
    subject=subject,
    html_content=html
  )
	if timestamp:
		print(timestamp)
		# email.send_at = SendAt(timestamp) ##########################################################################################################
	return email


def sendEmail(email):
	try:
		sg = SendGridAPIClient(environ.get('SENDGRID_KEY'))
		response = sg.send(email)
		print('Status Code:', response.status_code)
		print('Body:', response.body)
		print('Headers:\n', response.headers)
		return ''
	except Exception as e:
		print(e)
		return 'Error'


def createParticipantEmails(day, render_template, pairs, airtableParticipants):
	# get all opted in participants, but only with the necessary fields
	participants = {
		row['fields']['ID'] : row['fields'] for row in airtableParticipants.get_all(
			fields=[
				'ID','Name','Email','LinkedIn Profile','Day Preference','Opted In','Time Zone','Group'
			]
		)
	}

	emails = []
	week = getWeekString()
	boundaryTimestamp = timestamp("Wednesday", +00)
	# for each person to send profiles to this week
	for pairRecord in pairs:
		participant = participants[pairRecord["ID"]]

		sendAtTimestamp = timestamp(participant["Day Preference"], participant["Time Zone"])

		# if time to send is within 72 hours of Sunday 00:00 UTC, prepare it
		if ( (sendAtTimestamp <  boundaryTimestamp and day == "Sunday")
			or (sendAtTimestamp >= boundaryTimestamp and day == "Wednesday")):
			# render email template & add email object to list of emails to send NOW
			email = Email(
				to=participant["Email"],
				subject="New LinkedIn profiles to interact with | "+week+" | LinkedIn Pod Sorter",
				timestamp=sendAtTimestamp,
				html=render_template(
					"email.html",
					week=week,
					name=participant["Name"],
					userHash=hashID(pairRecord["ID"]),
					peopleToCommentOn=pairRecord["Profiles"],
					peopleThatWillComment=pairRecord["Profiles Assigned"],
					participants=participants,
					participating=True
				)
			)
			emails.append(email)
	return emails


def createNonParticipantEmails(render_template, airtableParticipants):
	emails = []
	nonparticipants = airtableParticipants.get_all(
		filterByFormula="{Opted In}=Blank()",
		fields=[
			'ID','Name','Email'
		]
	)
	# for each non participant this week (just before we make everyone opted out)
	for nonParticipant in nonparticipants:
		# render email template & add email object to list of emails to send NOW
		emails.append(Email(
			to=nonParticipant['fields']["Email"],
			subject="Are you participating next week? | LinkedIn Pod Sorter",
			html=render_template(
				"email.html",
				name=nonParticipant['fields']["Name"],
				userHash=hashID(nonParticipant['fields']["ID"]),
				participating=False
			),
		))
	return emails
