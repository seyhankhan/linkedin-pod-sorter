############ Seyhan Van Khan
############ Linkedin Pod Sorter
############ description
############ December 2020
# save linkedin profile URLs as 1 standard
# get requests are limited by 100. do batch instead
# send at certain times: use 'personalizations' https://github.com/sendgrid/sendgrid-python/issues/401
################################ IMPORT MODULES ################################


from base64 import b64decode, b64encode
from datetime import datetime
from json import dumps as json_dumps
from os import environ
from random import shuffle

from airtable import Airtable
from flask import Flask, render_template, redirect, request
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail


def base64_to_utf8(letters):
	letters += "=" * (4 - len(letters) % 4)
	return b64decode(letters.encode()).decode()

def utf8_to_base64(letters):
	return b64encode(letters.encode("utf-8")).decode("utf-8").replace("=","")


################################### INIT APP ###################################


app = Flask(__name__)
app.secret_key = "s14a"


##################################### INDEX ####################################


@app.route('/', methods=['GET', 'POST'])
def index():
	if request.method == 'GET':
		return render_template('index.html')
	else:
		airtable = Airtable(environ.get('AIRTABLE_TABLE'), 'Participants', environ.get('AIRTABLE_KEY'))
		record = {
	    "Name": request.form["name"],
	    "Email": request.form["email"],
	    "LinkedIn Profile": request.form["linkedinProfile"],
			"Time Zone": request.form["timezone"],
			"Opted In": True
		}
		if airtable.match('Email', request.form["email"]) or airtable.match('LinkedIn Profile', request.form["linkedinProfile"]):
			return render_template('index.html', userAlreadySignedUp='True')
		else:
			airtable.insert(record)
			errorOccured = sendEmail(Mail(
				from_email=environ.get('FROM_EMAIL'),
				to_emails=record["Email"],
				subject="You're in! Welcome to LinkedIn Pod Sorter",
				html_content=f"""
					Thank you {record['Name']} for signing up
					Just confirming your personal information:
					<br>
			    <br>Email: {record['Email']}
			    <br>LinkedIn Profile: {record['LinkedIn Profile']}
					<br>Time Zone: {record['Time Zone']}
					<br>
					<br>Regards,
					<br>LinkedIn Pod Sorter
				"""
			))
			if errorOccured == "Error":
				pass
			return redirect('/signup-confirmation')


############################## SIGNUP CONFIRMATION #############################


@app.route('/signup-confirmation')
def signup_confirmation():
	return render_template('signup-confirmation.html')


############################### TOPUP CONFIRMATION #############################


@app.route('/topup')
def topup_email_base64():
	airtable = Airtable(environ.get('AIRTABLE_TABLE'), 'Participants', environ.get('AIRTABLE_KEY'))
	matchingRecord = airtable.match("Email", base64_to_utf8(request.args['user']))

	if matchingRecord:
		airtable.update(matchingRecord['id'], {'Opted In': True})

	return redirect('/weeklyconfirmation')


############################### TOPUP CONFIRMATION #############################


@app.route('/weeklyconfirmation')
def weekly_confirmation():
	return render_template('topup-confirmation.html')


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


def sendWeeklyEmails(pairs):
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


##################### EMAIL ROUTE TO BE OPENED EVERY WEEK ######################


@app.route('/calculate-pairs/' + environ.get('EMAIL_CODE'), methods=['POST'])
def verifiedUser():
	pairs = calculateProfilePairs()
	addPairsToAirtable(pairs)
	sendWeeklyEmails(pairs)
	return redirect('/')


################################# OTHER ROUTES #################################


# @app.route('/<path:dummy>')
# def fallback(dummy):
# 	return redirect(url_for('index'))


#################################### APP RUN ###################################


if __name__ == "__main__":
    app.run(debug=True)
