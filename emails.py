from datetime import datetime, timedelta, date, time
from os import environ
from pytz import common_timezones, timezone
from random import shuffle
from time import sleep as time_sleep

from airtable import Airtable
from jinja2 import Environment, FileSystemLoader
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, SendAt

from hashing import hashID

DAYS = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
MAX_PROFILES_PER_PERSON = 15


################################ CALCULATE PAIRS ###############################


def generateAllPairsAndTimestamps(groups, day):
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
					"Timestamp": calculateEmailTimestamp(day, groups[group][participantIndex]["Time Zone"])
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


def clearAllDayPreferences(airtableTable):
	for row in airtableTable.get_all(filterByFormula="NOT({Day Preference}=Blank())"):
		airtableTable.update(row['id'], {"Day Preference": []})
		time_sleep(0.2)


##################################### TIME #####################################


def getAllTimezones():
	return common_timezones

def getCurrentDatetime():
	return timezone("UTC").localize(datetime.now()).date()


def getLastCommitEmailDate():
	# get the date right NOW
	# If before Sunday, 07:30 UTC:
	#			it was sent on the sunday the PREVIOUS week
	# If after Sunday, 07:30 UTC:
	#			it was today
	now = getCurrentDatetime()

	# email was just sent today, so it's today
	if now.weekday() == 6 and now.hour >= 7 and now.minute >= 30:
		return now.date()
	# if before Sunday, 07:30 UTC, it was last week's sunday
	else:
		return now.date() + timedelta(days=-now.weekday() - 1)


def calculateEmailTimestamp(userDay, userTimezone):
	# get date of when LAST commit email was sent
	# add days to make it the Day Preference
	nextUserDay = getLastCommitEmailDate() \
		+ timedelta(days=1 + DAYS.index(userDay))

	datetimeToSend = timezone(userTimezone).localize(
		datetime.combine(nextUserDay, time(7, 30))
	)
	return int(datetimeToSend.timestamp())


# 29 Dec - 2 Jan
def getWeekToCommitToRange():
	nextDeadline = getLastCommitEmailDate()
	monday = nextDeadline + timedelta(days=1)
	friday = nextDeadline + timedelta(days=5)
	# Add monday's month if different to friday's
	extraMonth = " %b" if monday.month != friday.month else ""
	return monday.strftime("%-d" + extraMonth) + " - " + friday.strftime("%-d %b")


# list of every weekday & its full date
def getTopupWeekdayOptions():
	lastSunday = getLastCommitEmailDate()
	options = []
	for i in range(0 + 1, 5 + 1):
		weekday = lastSunday + timedelta(days=i)
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
		print(to, timestamp)
		email.send_at = SendAt(timestamp)
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


def renderHTML(file_name, **context):
	return Environment(
		loader=FileSystemLoader('templates/')
	).get_template(file_name).render(context)


# Runs Mon-Fri, at 07:30 UTC
# (should be running 1930 day before)
def createProfilesEmail(participants, pairs):
	emails = []

	# for each email to send profiles to this week
	for pairRecord in pairs:
		participant = participants[pairRecord["ID"]]

		sendAtTimestamp = pairRecord["Timestamp"]
		emailDate = datetime.fromtimestamp(sendAtTimestamp).strftime("%-d %b")

		# render email template & add email object to list of emails to send NOW
		emails.append(Email(
			to=participant["Email"],
			subject=emailDate + " TODAY’s LinkedIn Squad",
			timestamp=sendAtTimestamp,
			html=renderHTML(
				"emails/profiles.html",
				name=participant["Name"],
				userHash=hashID(pairRecord["ID"]),
				peopleToCommentOn=pairRecord["Profiles"],
				peopleThatWillComment=pairRecord["Profiles Assigned"],
				participants=participants
			)
		))
	return emails


# runs on Sunday 07:30 UTC
def createCommitEmails(participants):
	nextWeekRange = getWeekToCommitToRange()

	emails = []
	for participant in participants.values():
		emails.append(Email(
			to=participant["Email"],
			subject="Are you participating next week? ("+nextWeekRange+") | LinkedIn Pod Sorter",
			html=renderHTML(
				"emails/commit.html",
				name=participant["Name"],
				userHash=hashID(participant["ID"]),
				nextWeekRange=nextWeekRange,
			)
		))
	return emails
