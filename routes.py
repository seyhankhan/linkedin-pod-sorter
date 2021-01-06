############ Seyhan Van Khan
############ Linkedin Pod Sorter
############ description
############ December 2020
# TURN 'OPTED IN' OFF FOR ALL
# save linkedin profile URLs as 1 standard
# get requests are limited by 100? do batch instead
# (if using sendgrid, use 'personalizations' github.com/sendgrid/sendgrid-python/issues/401)
"""
send at certain times
	bi-weekly wayscript runs script to schedule emails

"""
################################ IMPORT MODULES ################################


from json import dumps as json_dumps
from os import environ
from time import sleep as time_sleep

from flask import Flask, render_template, redirect, request, url_for

from emails import *

################################### INIT APP ###################################


app = Flask(__name__)
app.secret_key = "s14a"


##################################### INDEX ####################################


@app.route('/', methods=['GET', 'POST'])
@app.route('/sandbox', methods=['GET', 'POST'])
def index():
	if request.method == 'GET':
		return render_template('index.html')
	else:
		group = "Sandbox" if "sandbox" in request.path else "Public"

		airtable = Airtable(environ.get('AIRTABLE_WANDERN_TABLE'), 'Participants', environ.get('AIRTABLE_KEY'))
		record = {
	    "Name": request.form["name"],
	    "Email": request.form["email"],
	    "LinkedIn Profile": request.form["linkedinProfile"],
			"Day Preference": request.form["dayPreference"],
			"Time Zone": int(request.form["timezone"]),
			"Group": group
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


##################### EMAIL ROUTE TO BE OPENED EVERY WEEK ######################

"""
TIMELINE:
Sunday, 00:00 UTC
		All pairs are calculated
		Pairs IDs saved on Airtable 'Pairs' table
		Send all scheduled emails due up to Tuesday 23:59 UTC

Wednesday, 00:00 UTC
		Get remaining pairs from airtable
		Send all remaining scheduled emails up to Friday 23:59 UTC
"""

# covers Sunday 0000 UTC to Tuesday 23:59 UTC
# first email is sent Sunday 19:30 UTC (New Zealand)
@app.route('/sunday/')# + environ.get('EMAIL_CODE'), methods=['POST'])
def weeklyEmailCalculation_Sunday():
	# get list of participants
	airtableParticipants = Airtable(environ.get('AIRTABLE_LINKEDIN_TABLE'), 'Participants', environ.get('AIRTABLE_KEY'))

	pairs = []
	for group in ['Sandbox','Public']:
		pairs.extend(calculateProfilePairs(group, airtableParticipants))

	addPairsToAirtable(pairs)

	emails = createParticipantEmails("Sunday", render_template, pairs, airtableParticipants)
	emails.append(createNonParticipantEmails(render_template, airtableParticipants))

	# now send each email
	# if error occurs, output & stop sending emails
	for email in emails:
		sendEmail(email)
		break
		if sendEmail(email) == 'Error':
			break

	# make everyone now OPTED OUT
	# if they want to opt back in, they will need to click link in email
	optOutEveryone(airtableParticipants)

	return redirect("/")





################################### WEDNESDAY ##################################



# covers Wednesday 00:00 UTC to Friday 23:59 UTC
# last email is sent at Friday 17:30 UTC (Hawaii)
@app.route('/wednesday/' + environ.get('EMAIL_CODE'), methods=['POST'])
def weeklyEmailCalculation_Wednesday():
	# get list of participants
	airtableParticipants = Airtable(environ.get('AIRTABLE_LINKEDIN_TABLE'), 'Participants', environ.get('AIRTABLE_KEY'))

	airtablePairs = Airtable(environ.get('AIRTABLE_LINKEDIN_TABLE'), 'Pairs', environ.get('AIRTABLE_KEY'))
	pairs = [
		{
			'ID': 								row['fields']['ID'],
			'Profiles' : 				 	[int(id) for id in row['fields']['Profiles'].split(",")],
			'Profiles Assigned' : [int(id) for id in row['fields']['Profiles Assigned'].split(",")],
		} for row in airtablePairs.get_all()
	]

	emails = createParticipantEmails("Wednesday", render_template, pairs, airtableParticipants)
	# now send each email
	# if error occurs, output & end the function
	for email in emails:
		if sendEmail(email) == 'Error':
			return

	return redirect('/')


#################################### TOPUP #####################################


@app.route('/topup')
def topup():
	# add case if no user is provided
	airtable = Airtable(environ.get('AIRTABLE_LINKEDIN_TABLE'), 'Participants', environ.get('AIRTABLE_KEY'))
	if 'user' not in request.args:
		return redirect("/")
	matchingRecord = airtable.match("ID", unhashID(request.args['user']))
	if matchingRecord:
		airtable.update(matchingRecord['id'], {'Opted In': True})
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

		airtableParticipants = Airtable(environ.get('AIRTABLE_LINKEDIN_TABLE'), 'Participants', environ.get('AIRTABLE_KEY'))
		airtablePairs = Airtable(environ.get('AIRTABLE_LINKEDIN_TABLE'), 'Pairs', environ.get('AIRTABLE_KEY'))

		# get list of participants that are currently opted in
		participants = {
			record['fields']['ID'] : record['fields'] for record in airtableParticipants.get_all()
		}

		userPairs = airtablePairs.match("ID", str(userID))
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
		airtableParticipants = Airtable(environ.get('AIRTABLE_LINKEDIN_TABLE'), 'Participants', environ.get('AIRTABLE_KEY'))

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


############################### FEEDBACK CONFIRMATION #############################


@app.route('/feedback-confirmation')
def feedback_confirmation():
	return render_template('feedback-confirmation.html')


################################# OTHER ROUTES #################################


# @app.route('/<path:dummy>')
# def fallback(dummy):
# 	return redirect(url_for('index'))


#################################### APP RUN ###################################


if __name__ == "__main__":
	app.run(debug=True)
