############ Seyhan Van Khan
############ Linkedin Pod Sorter
############ description
############ December 2020
# TURN 'OPTED IN' OFF FOR ALL
# save linkedin profile URLs as 1 standard
# get requests are limited by 100? do batch instead
# (if using sendgrid, use 'personalizations' github.com/sendgrid/sendgrid-python/issues/401)
"""
Every week, every person chooses 1 or multiple days for next weeks pod sorting.
If they pick multiple, they are in every group & emailed the pairs for that group for every day they picked that week.
If they dont fill in that form, they are not emailed at all
"""
DEBUG_MODE = False
PEOPLE_TABLE = "Seyhan's testing group" if DEBUG_MODE else 'Members'
################################ IMPORT MODULES ################################


from itertools import product
from json import dumps as json_dumps
from os import environ
from time import sleep as time_sleep

from random import shuffle

from flask import Flask, render_template, redirect, request, url_for

from emails import *
from hashing import hashID, unhashID


################################### INIT APP ###################################


app = Flask(__name__)
app.secret_key = "s14a"


##################################### INDEX ####################################


@app.route('/', methods=['GET', 'POST'])
@app.route('/sandbox', methods=['GET', 'POST'])
def index():
	if request.method == 'GET':
		return render_template(
			'index.html',
			formAction=request.path,
			timezones=getAllTimezones()
		)
	else: # POST
		group = "Sandbox" if "sandbox" in request.path.lower() else "GTeX"

		airtable = Airtable(environ.get('AIRTABLE_LINKEDIN_TABLE'), PEOPLE_TABLE, environ.get('AIRTABLE_KEY'))
		record = {
			"Name": request.form["name"],
			"Email": request.form["email"],
			"LinkedIn Profile": request.form["linkedinProfile"],
			"Time Zone": request.form["timezone"],
			"Group": [group]
		}
		if airtable.match('Email', request.form["email"]) or airtable.match('LinkedIn Profile', request.form["linkedinProfile"]):
			return render_template(
				'index.html',
				formAction=request.path,
				timezones=getAllTimezones(),
				userAlreadySignedUp='True'
			)
		newRow = airtable.insert(record)
		errorOccured = sendEmail(Email(
			to=record["Email"],
			subject="POD Confirmation",
			html=render_template(
				"signup-email.html",
				name=record['Name'],
				group=group,
				userHash=hashID(newRow['fields']['ID'])
			)
		))
		if errorOccured == "Error":
			pass
		return redirect('/signup-confirmation')


############################## SIGNUP CONFIRMATION #############################


@app.route('/signup-confirmation')
def signup_confirmation():
	return render_template('signup-confirmation.html')


#############################################


@app.route('/commit')
def commit():
	if not('user' in request.args and unhashID(request.args['user']) >= 0):
		return render_template(
			"topup.html",
			validID=False
		)
	airtable = Airtable(environ.get('AIRTABLE_LINKEDIN_TABLE'), PEOPLE_TABLE, environ.get('AIRTABLE_KEY'))

	airtable.update_by_field("ID", unhashID(request.args['user']), {'Opted In': True, "Day Preference": ['Thursday']})
	# add error page if ID not found
	return redirect('/weeklyconfirmation')


@app.route('/specialWednesdayBobBobBobbity')
def specialWednesday():
	airtableParticipants = Airtable(environ.get('AIRTABLE_LINKEDIN_TABLE'), PEOPLE_TABLE, environ.get('AIRTABLE_KEY'))
	participants = {
		row['fields']['ID'] : row['fields'] for row in airtableParticipants.get_all(
			fields=[
				'ID','Name','Email','LinkedIn Profile','Day Preference','Opted In','Time Zone','Group'
			]
		)
	}

	emails = []
	for participant in participants.values():
		# render email template & add email object to list of emails to send NOW
		emails.append(Email(
			to=participant["Email"],
			subject="Are you participating tomorrow? (14 Jan) | LinkedIn Pod Sorter",
			html=render_template(
				"emails/weekly2.html",
				name=participant["Name"],
				userHash=hashID(participant["ID"])
			)
		))
	# now send each email
	# if error occurs, output & stop sending emails
	for email in emails[:3]:
		print(sendEmail(email))



	return redirect("/")


##################### EMAIL ROUTE TO BE OPENED EVERY WEEK ######################


"""
TIMELINE:
Sunday, 19:00 UTC
		All pairs are calculated
		Pairs IDs saved on Airtable 'Emails' table
		Timestamp is saved for any emails to be sent AFTER 1900 Wednesday - THE CUTOFF
		Send all scheduled emails due within range:
			First email sent Sunday, 19:30 UTC (New Zealand)
			Last email sent Wednesday, 18:59 UTC

Wednesday, 18:00 UTC
		Get remaining pairs & timestamps from airtable (only get rows with timestamps)
		Send all remaining scheduled emails up to Saturday 17:59 UTC
		last email is sent at Friday 17:30 UTC (Hawaii)
"""

# runs at Sunday 19:00 UTC
# covers Sunday 19:00 UTC to Wednesday 18:59 UTC
# first email is sent Sunday 19:30 UTC (New Zealand)
@app.route('/sunday/')# + environ.get('EMAIL_CODE'), methods=['POST'])
def weeklyEmailCalculation_Sunday():
	# get list of participants
	airtableParticipants = Airtable(environ.get('AIRTABLE_LINKEDIN_TABLE'), PEOPLE_TABLE, environ.get('AIRTABLE_KEY'))
	participants = {
		row['fields']['ID'] : row['fields'] for row in airtableParticipants.get_all(
			fields=[
				'ID','Name','Email','LinkedIn Profile','Day Preference','Opted In','Time Zone','Group'
			]
		)
	}

	groups = {}
	for person in participants.values():
		if "Opted In" not in person:
			continue
		for group, day in product(person['Group'], person['Day Preference']):
			if group in groups:
				if day in groups[group]:
					groups[group][day].append(person)
				else:
					groups[group][day] = [person]
			else:
				groups[group] = {day: [person]}

	pairs = generateAllPairsAndTimestamps(groups, participants)

	addPairsToAirtable(pairs)

	emails = createParticipantEmails("Sunday", render_template, pairs, participants)
	emails.extend(createNonParticipantEmails(render_template, participants))

	# now send each email
	# if error occurs, output & stop sending emails
	for email in emails:
		sendEmail(email)
		break
		print(sendEmail(email))


	# make everyone now OPTED OUT
	# if they want to opt back in, they will need to click link in email
	optOutEveryone(airtableParticipants)

	return redirect("/")


################################### WEDNESDAY ##################################


# runs at Wednesday 18:00 UTC
# covers Wednesday 19:00 UTC to Saturday 17:59 UTC
# last email is sent at Friday 17:30 UTC (Hawaii)
@app.route('/wednesday/' + environ.get('EMAIL_CODE'), methods=['POST'])
def weeklyEmailCalculation_Wednesday():
	# get list of participants
	airtableParticipants = Airtable(environ.get('AIRTABLE_LINKEDIN_TABLE'), PEOPLE_TABLE, environ.get('AIRTABLE_KEY'))
	participants = {
		row['fields']['ID'] : row['fields'] for row in airtableParticipants.get_all(
			fields=[
				'ID','Name','Email','LinkedIn Profile'
			]
		)
	}
	airtablePairs = Airtable(environ.get('AIRTABLE_LINKEDIN_TABLE'), 'Emails', environ.get('AIRTABLE_KEY'))
	pairs = [
		{
			'ID' : 								row['fields']['ID'],
			'Profiles' : 				 	[int(id) for id in row['fields']['Profiles'].split(",")],
			'Profiles Assigned' : [int(id) for id in row['fields']['Profiles Assigned'].split(",")],
			"Timestamp" : 				row['fields']['Timestamp']
		} for row in airtablePairs.get_all()
	]

	emails = createParticipantEmails("Wednesday", render_template, pairs, participants)
	# now send each email
	# if error occurs, output & end the function
	for email in emails:
		print(sendEmail(email))

	return redirect('/')


#################################### TOPUP #####################################


@app.route('/topup', methods=['GET','POST'])
def topup():
	if not('user' in request.args and unhashID(request.args['user']) >= 0):
		return render_template(
			"topup.html",
			validID=False
		)

	if request.method == "GET":
		return render_template(
			"topup.html",
			validID=True,
			userHash=request.args['user'],
			nextWeekRange=getNextWeekToOptInRange(),
			dayOptions=getTopupWeekdayOptions()
		)
	else: # POST
		airtable = Airtable(environ.get('AIRTABLE_LINKEDIN_TABLE'), PEOPLE_TABLE, environ.get('AIRTABLE_KEY'))
		# add error page if ID not found
		airtable.update_by_field("ID", unhashID(request.args['user']), {'Opted In': True, "Day Preference": list(dict(request.form).keys())})
		return redirect('/weeklyconfirmation')


############################## TOPUP CONFIRMATION ##############################


@app.route('/weeklyconfirmation')
def topup_confirmation():
	return render_template('topup-confirmation.html')


################################### FEEDBACK ###################################


@app.route('/feedback', methods=['GET', 'POST'])
def feedback():
	if request.method == "GET":
		# get user's pairs
		# list them all with 3 buttons for each for feedback (all optional)
		# list all people that are assigned to them with 3 butons for feedback (all optional)
		# submit on airtable
		if 'user' not in request.args:
			return redirect("/")
		userID = unhashID(request.args['user'])

		airtableParticipants = Airtable(environ.get('AIRTABLE_LINKEDIN_TABLE'), PEOPLE_TABLE, environ.get('AIRTABLE_KEY'))
		airtablePairs = Airtable(environ.get('AIRTABLE_LINKEDIN_TABLE'), 'Emails', environ.get('AIRTABLE_KEY'))

		# get list of participants that are currently opted in
		participants = {
			record['fields']['ID'] : record['fields'] for record in airtableParticipants.get_all()
		}

		userPairs = airtablePairs.match("ID", userID)
		profilesIDs = userPairs["fields"]["Profiles"].split(",")
		profilesAssignedIDs = userPairs["fields"]["Profiles Assigned"].split(",")

		peopleToCommentOn = 		[participants[int(id)] for id in profilesIDs]
		peopleThatWillComment = [participants[int(id)] for id in profilesAssignedIDs]


		return render_template(
			"feedback.html",
			peopleToCommentOn=peopleToCommentOn,
			peopleThatWillComment=peopleThatWillComment,
			userHash=request.args['user']
		)
	else: # POST
		airtableParticipants = Airtable(environ.get('AIRTABLE_LINKEDIN_TABLE'), PEOPLE_TABLE, environ.get('AIRTABLE_KEY'))

		# get list of participants that are currently opted in
		participants = {
			record['fields']['ID'] : record['fields'] for record in airtableParticipants.get_all()
		}

		recordsToUpdate = {}
		for feedback in dict(request.form).keys():
			id = 								int(feedback.split("-")[1])
			feedbackCategory = 	feedback.split("-")[0]
			feedbackCount = 		participants[id][feedbackCategory] + 1

			if id in recordsToUpdate:
				recordsToUpdate[id][feedbackCategory] = feedbackCount
			else:
				recordsToUpdate[id] = {feedbackCategory: feedbackCount}

		print(json_dumps(recordsToUpdate, indent=4))

		for ID in recordsToUpdate:
			airtableParticipants.update_by_field("ID", ID, recordsToUpdate[ID])
			time_sleep(0.2)

		return redirect("/feedback-confirmation")


############################ FEEDBACK CONFIRMATION #############################


@app.route('/feedback-confirmation')
def feedback_confirmation():
	return render_template('feedback-confirmation.html')


################################# VIEW EMAILS ##################################


if DEBUG_MODE:
	@app.route('/signupemail')
	def viewSignupEmail():
		airtableParticipants = Airtable(environ.get('AIRTABLE_LINKEDIN_TABLE'), PEOPLE_TABLE, environ.get('AIRTABLE_KEY'))
		participants = {
			row['fields']['ID'] : row['fields'] for row in airtableParticipants.get_all(
				fields=[
					'ID','Name','Email','LinkedIn Profile','Day Preference','Opted In','Time Zone','Group'
				]
			)
		}
		return render_template(
			"emails/signup.html",
			name="Scott Spiderman",
			group="Sandbox",
			userHash=hashID(114)
		)


	@app.route('/weeklyemail')
	def viewWeeklyEmail():
		airtableParticipants = Airtable(environ.get('AIRTABLE_LINKEDIN_TABLE'), PEOPLE_TABLE, environ.get('AIRTABLE_KEY'))
		participants = {
			row['fields']['ID'] : row['fields'] for row in airtableParticipants.get_all(
				fields=[
					'ID','Name','Email','LinkedIn Profile','Day Preference','Opted In','Time Zone','Group'
				]
			)
		}

		return render_template(
			"emails/weekly.html",
			name="Scott Spiderman",
			userHash=hashID(114),
			peopleToCommentOn=[110,111,112],
			peopleThatWillComment=[120,121,122],
			participants=participants,
			participating=True,
			nextWeekRange="8 - 12 Jan"
		)


############################### GOOGLE DOCS TIPS ###############################


@app.route('/tips')
def linkedinPodTips():
	return redirect("https://docs.google.com/document/d/1JkJmkpSqJdwur7pFF14aTcT7senipRNj3b8lIK5ns8U/edit?usp=sharing")


################################# OTHER ROUTES #################################


# @app.route('/<path:dummy>')
# def fallback(dummy):
# 	return redirect(url_for('index'))


#################################### APP RUN ###################################


if __name__ == "__main__":
	app.run(debug=DEBUG_MODE)
