############ Seyhan Van Khan
############ Linkedin Pod Sorter
############ description
############ December 2020
# save linkedin profile URLs as 1 standard

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


def calculatePairsOnAirtable():
	airtable = Airtable(environ.get('AIRTABLE_TABLE'), 'Participants', environ.get('AIRTABLE_KEY'))
	participants = airtable.get_all(filterByFormula="NOT({Opted In}=Blank())")
	numParticipants = len(participants)

	print(json_dumps(participants, indent=4))
	shuffle(participants)

	MAX_PAIRS_PER_PERSON = 14
	if numParticipants < 14 + 1:
		MAX_PAIRS_PER_PERSON = numParticipants - 1

	# range of numbers from 1 to max pairs per person
  # 1,2,3,4,5,6,7,8,9,10,11,12,13,14
	pairs = []
	for participantIndex in range(numParticipants):
		pairs.append({
			"ID": str(participants[participantIndex]['fields']["ID"]),
			"This weeks pairs": ",".join(
				str(participants[(participantIndex + indexPair + 1) % numParticipants]['fields']["ID"]) for indexPair in range(MAX_PAIRS_PER_PERSON)
			)
		})

	airtablePairs = Airtable(environ.get('AIRTABLE_TABLE'), 'Pairs', environ.get('AIRTABLE_KEY'))

	airtablePairs.batch_delete([record['id'] for record in airtablePairs.get_all()])

	airtablePairs.batch_insert(pairs)


	print(json_dumps(pairs, indent=4))


############################## EMAIL LIST OF PEOPLE ############################


def createEmailContent(name, pairs, userHash, optedIn=True):
	if optedIn:
		template = f"""
			<html>
				<head>
					<meta charset="utf-8">
					<meta name="author" content="Seyhan Van Khan">
					<meta name="description" property="og:description" content="Your list of new LinkedIn profiles is here!">
					<title>Pod Sorter for LinkedIn</title>
				</head>
				<body style="color:black">
					Hey {name},
					<br />
					<br />
					Click here to confirm your participation for the next week: https://linkedin-pod-sorter.herokuapp.com/topup?user={userHash}
					<br />
					The following participants will post on LinkedIn today - go and check out their activity
					<ul>
		"""
		for pair in pairs:
			template += f"<li>{pair['Name']} - {pair['LinkedIn Profile']}</li>"

		template += f"""
					</ul>
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
				</head>
				<body style="color:black">
					Hey {name},
					<br />
					<br />
					Click here to confirm your participation for next week: https://linkedin-pod-sorter.herokuapp.com/topup?user={userHash}
					<br />
					Linkedin Pod Sorter
				</body>
			</html>
		"""
	return template

def emailListOfPeople():
	airtablePairs = Airtable(environ.get('AIRTABLE_TABLE'), 'Pairs', environ.get('AIRTABLE_KEY'))
	pairs = airtablePairs.get_all()

	airtableParticipants = Airtable(environ.get('AIRTABLE_TABLE'), 'Participants', environ.get('AIRTABLE_KEY'))
	participantsRAW = airtableParticipants.get_all(filterByFormula="NOT({Opted In}=Blank())")
	participants = {record['fields']['ID']: record['fields'] for record in participantsRAW}
	print(json_dumps(participants,indent=4))
	messages = []
	# for each person in the table
	for pair in pairs:
		# record of participant to send to
		record = participants[int(pair["fields"]["ID"])]
		# parse the list of pairs in pairs column into LIST OF PARTICIPANT IDs
		# make a list with each participant ID's record
		# these are participants that the person above has to comment & like for
		emailList = [participants[int(id)] for id in pair["fields"]["This weeks pairs"].split(',')]

		messages.append(
			Mail(
		    from_email=environ.get('FROM_EMAIL'),
		    to_emails=record['Email'],
		    subject='LinkedIn Pod Sorter - Your LinkedIn profiles for this week',
		    html_content=createEmailContent(record['Name'], emailList, utf8_to_base64(record["Email"]))
	  	)
		)
	print(messages)

	for message in messages:
		try:
			sg = SendGridAPIClient(environ.get('SENDGRID_KEY'))
			response = sg.send(message)
			print(response.status_code)
			print(response.body)
			print(response.headers)
		except Exception as e:
			print(e)
			return

	nonparticipants = airtableParticipants.get_all(filterByFormula="{Opted In}=Blank()")
	for nonParticipant in nonparticipants:
		try:
			sg = SendGridAPIClient(environ.get('SENDGRID_KEY'))
			response = sg.send(
				Mail(
			    from_email=environ.get('FROM_EMAIL'),
			    to_emails=nonParticipant['fields']['Email'],
			    subject='LinkedIn Pod Sorter - Are you going to participate next week?',
			    html_content=createEmailContent(nonParticipant['fields']['Name'], [], utf8_to_base64(nonParticipant['fields']["Email"]), optedIn=False)
	  		)
			)
			print(response.status_code)
			print(response.body)
			print(response.headers)
		except Exception as e:
			print(e)
			return


######################## EMAIL ROUTE TO BE OPENED AT 8AM #######################


@app.route('/calculate-pairs/' + environ.get('EMAIL_CODE'), methods=['POST'])
def verifiedUser():
	calculatePairsOnAirtable()
	emailListOfPeople()
	return redirect('/')


################################# OTHER ROUTES #################################


# @app.route('/<path:dummy>')
# def fallback(dummy):
# 	return redirect(url_for('index'))


#################################### APP RUN ###################################


if __name__ == "__main__":
    app.run(debug=True)
