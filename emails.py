from os import environ

from jinja2 import Environment, FileSystemLoader
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, SendAt

from hashing import hashID


##################################### EMAIL ####################################


def renderHTML(file_name, **context):
	return Environment(
		loader=FileSystemLoader('templates/')
	).get_template(file_name).render(context)


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


def sendEmails(emails):
	sg = SendGridAPIClient(environ.get('SENDGRID_KEY'))
	for email in emails:
		try:
			response = sg.send(email)
			print('Status Code:', response.status_code)
			print('Body:', response.body)
			print('Headers:\n', response.headers)
		except Exception as e:
			print(e)


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


################################# CREATE EMAILS ################################


def createSignupEmail(to, name, group, IDhash, weekToCommitTo):
	print(IDhash)
	return Email(
		to=to,
		subject="POD Confirmation",
		html=renderHTML(
			"emails/signup.html",
			name=name,
			group=group,
			userHash=IDhash,
			weekToCommitTo=weekToCommitTo
		)
	)

# Runs Mon-Fri, at 07:30 UTC
# (should be running 1930 day before)
def createProfilesEmail(participants, pairs, emailDate):
	emails = []

	# for each email to send profiles to this week
	for pairRecord in pairs:
		participant = participants[pairRecord["ID"]]

		sendAtTimestamp = pairRecord["Timestamp"]

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
def createCommitEmails(participants, timestamp, weekToCommitTo):
	emails = []
	for participant in participants.values():
		emails.append(Email(
			to=participant["Email"],
			subject="Are you participating next week? ("+weekToCommitTo+") | LinkedIn Pod Sorter",
			timestamp=timestamp,
			html=renderHTML(
				"emails/commit.html",
				name=participant["Name"],
				userHash=hashID(participant["ID"]),
				weekToCommitTo=weekToCommitTo,
			)
		))
	return emails
