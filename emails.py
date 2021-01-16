from os import environ
from random import shuffle

from airtables import Airtable
from jinja2 import Environment, FileSystemLoader
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, SendAt

from hashing import hashID
from constants import *


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
def createCommitEmails(participants, timestamp):
	nextWeekRange = getWeekToCommitToRange()

	emails = []
	for participant in participants.values():
		emails.append(Email(
			to=participant["Email"],
			subject="Are you participating next week? ("+nextWeekRange+") | LinkedIn Pod Sorter",
			timestamp=timestamp
			html=renderHTML(
				"emails/commit.html",
				name=participant["Name"],
				userHash=hashID(participant["ID"]),
				nextWeekRange=nextWeekRange,
			)
		))
	return emails
