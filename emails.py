from datetime import datetime, timedelta, date, time
from os import environ
from pytz import common_timezones, timezone
from random import shuffle
from time import sleep as time_sleep

from airtable import Airtable
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, SendAt

DAYS = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
MAX_PROFILES_PER_PERSON = 14


################################ CALCULATE PAIRS ###############################


def generateAllPairsAndTimestamps(groups, allParticipants):
	pairsRows = []
	for group in groups:
		for day in groups[group]:
			participants = allParticipants[group][day]
			numParticipants = len(participants)

			shuffle(participants)

			# range of numbers from 1 to max profiles per person
		  # 1,2,3,4,5,6,7,8,9,10,11,12,13,14
			profilePairIndices = range(1, min(MAX_PROFILES_PER_PERSON, numParticipants - 1) + 1)

			pairs = []
			# for each participant
			for participantIndex in range(numParticipants):
				pairs.append(
					{
						"ID": participants[participantIndex]["ID"],
						"Profiles": [
							participants[(participantIndex + i) % numParticipants]["ID"] for i in profilePairIndices
						],
						"Profiles Assigned": [
							participants[(participantIndex - i) % numParticipants]["ID"] for i in profilePairIndices
						],
						"Timestamp": calculateEmailTimestamp(day, participants[participantIndex]["Time Zone"])
					}
				)
			pairsRows.extend(pairs)
	return pairsRows


def addPairsToAirtable(pairs):
	airtablePairs = Airtable(environ.get('AIRTABLE_LINKEDIN_TABLE'), 'Emails', environ.get('AIRTABLE_KEY'))
	# clear every row from 'Emails' table
	airtablePairs.batch_delete([record['id'] for record in airtablePairs.get_all()])
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


def optOutEveryone(airtableTable):
	for row in airtableTable.get_all(filterByFormula="NOT({Opted In}=Blank())"):
		airtableTable.update(row['id'], {"Opted In" : False, "Day Preference": []})
		time_sleep(0.2)


##################################### TIME #####################################


def getAllTimezones():
	return common_timezones


def getNextDeadlineToOptIn():
	# get the date right NOW
	# If before Sunday, 19:00 UTC:
	#			it's THAT sunday that is the deadline
	# If after Sunday, 19:00 UTC:
	#			it's not this sunday, its the NEXT sunday after this ^
	now = datetime.now(timezone("UTC"))

	# we've already passed next weeks deadline. So we need to go to NEXT weeks sunday
	if now.weekday() == 6 and now.hour >= 19:
		nextDeadlineSunday = now.date() + timedelta(weeks=1)

	# its this weeks sunday (if today is sunday, ITS TODAY!)
	else:
		nextDeadlineSunday = now.date() + timedelta(days=-now.weekday() + 6)

	return datetime.combine(nextDeadlineSunday, time(19, tzinfo=timezone("UTC")))


# always calculated on a sunday, 19:00 UTC
def calculateEmailTimestamp(userDay, userTimezone):
	# get next deadline to sign up to the next week
	# and minus a week to get the current ongoing one
	# add days to make it the Day Preference
	nextUserDay = getNextDeadlineToOptIn().date() \
		+ timedelta(weeks=-1, days=DAYS.index(userDay) + 1)

	datetimeToSend = datetime.combine(
		nextUserDay,
		time(7, 30, tzinfo=timezone(userTimezone))
	)
	return int(datetimeToSend.timestamp())


# 29 Dec - 2 Jan
def getNextWeekToOptInRange():
	nextDeadline = getNextDeadlineToOptIn().date()
	monday = nextDeadline + timedelta(days=1)
	friday = nextDeadline + timedelta(days=5)
	# Add monday's month if different to friday's
	extraMonth = " %b" if monday.month != friday.month else ""
	return monday.strftime("%-d" + extraMonth) + " - " + friday.strftime("%-d %b")

# list of every weekday & its full date
def getTopupWeekdayOptions():
	nextDeadline = getNextDeadlineToOptIn().date()
	options = []
	for i in range(1, 5 + 1):
		weekday = nextDeadline + timedelta(days=i)
		options.append({
			'date'	:	weekday.strftime("%A, %-d %b"),
			'value'	:	weekday.strftime("%A")
		})
	return options


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
		email.send_at = SendAt(timestamp) ##########################################################################################################
	return email


def sendEmail(email):
	try:
		sg = SendGridAPIClient(environ.get('SENDGRID_KEY'))
		response = sg.send(email)
		print('Status Code:', response.status_code)
		print('Body:', response.body)
		print('Headers:\n', response.headers)
		return 'SENT'
	except Exception as e:
		print(e)
		return 'ERROR'


# runs on Sunday 19:00 UTC and Wednesday 18:00 UTC
def createParticipantEmails(day, render_template, pairs, participants):
	emails = []

	# get the next sunday deadline possible
	# go back to the last wednesday before that Sunday
	boundaryTimestamp = int(datetime.combine(
		getNextDeadlineToOptIn().date() - timedelta(days=4),
		time(19, tzinfo=timezone("UTC"))
	).timestamp())

	# for each email to send profiles to this week
	for pairRecord in pairs:
		participant = participants[pairRecord["ID"]]

		sendAtTimestamp = pairRecord["Timestamp"]
		emailDate = datetime.fromtimestamp(sendAtTimestamp).strftime("%-d %b")
		nextWeekRange = getNextWeekToOptInRange()

		# if time to send is within 72 hours of Sunday 19:00 UTC, prepare it
		if ( (sendAtTimestamp <  boundaryTimestamp and day == "Sunday")
			or (sendAtTimestamp >= boundaryTimestamp and day == "Wednesday")):
			# render email template & add email object to list of emails to send NOW
			emails.append(Email(
				to=participant["Email"],
				subject=emailDate + " TODAY’s LinkedIn Squad",
				timestamp=sendAtTimestamp,
				html=render_template(
					"emails/weekly.html",
					name=participant["Name"],
					userHash=hashID(pairRecord["ID"], participant["Name"]),
					nextWeekRange=nextWeekRange,
					participating=True,
					peopleToCommentOn=pairRecord["Profiles"],
					peopleThatWillComment=pairRecord["Profiles Assigned"],
					participants=participants
				)
			))
	return emails

# runs on Sunday 07:30 UTC
def createSundayCommitEmails(render_template, participants):
	emails = []
	# for each non participant this week (just before we make everyone opted out)
	for participant in participants.values():
		nextWeekRange = getNextWeekToOptInRange()
		# render email template & add email object to list of emails to send NOW
		emails.append(Email(
			to=nonParticipant["Email"],
			subject="Are you participating next week? ("+nextWeekRange+") | LinkedIn Pod Sorter",
			html=render_template(
				"emails/profiles.html",
				name=participant["Name"],
				userHash=hashID(participant["ID"], participant["Name"]),
				nextWeekRange=nextWeekRange,
				participating=False
			)
		))
	return emails
