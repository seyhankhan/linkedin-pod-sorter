############ Seyhan Van Khan
############ Linkedin Pod Sorter
############ description
############ December 2020
# TURN 'OPTED IN' OFF FOR ALL
# save linkedin profile URLs as 1 standard
# get requests are limited by 100? do batch instead
# (if using sendgrid, use 'personalizations' github.com/sendgrid/sendgrid-python/issues/401)
"""
Every week, every person chooses 1 or multiple days for next weeks pod sorting on SUNDAY EMAIL
If they pick multiple, they are in every group & emailed the pairs for that group for every day they picked that week.
If they dont fill in that form, they are not emailed at all

"""
################################ IMPORT MODULES ################################


from flask import Flask, render_template, redirect, request, url_for

from airtables import Airtable
from constants import DEBUG_MODE
from datetimes import *
from emails import createSignupEmail, sendEmail
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

		airtable = Airtable("Participants")
		record = {
			"Name": request.form["name"],
			"Email": request.form["email"],
			"LinkedIn Profile": request.form["linkedinProfile"],
			"Time Zone": request.form["timezone"],
			"Group": group
		}
		if airtable.match('Email', request.form["email"]) or airtable.match('LinkedIn Profile', request.form["linkedinProfile"]):
			return render_template(
				'index.html',
				formAction=request.path,
				timezones=getAllTimezones(),
				userAlreadySignedUp='True'
			)
		newRow = airtable.insert(record)
		errorOccured = sendEmail(createSignupEmail(
			to=record["Email"],
			name=record['Name'],
			group=group,
			IDhash=hashID(newRow['fields']['ID']),
			weekToCommitTo=getWeekToCommitToRange()
		))
		if errorOccured == "ERROR":
			pass
		return redirect('/signup-confirmation')


############################## SIGNUP CONFIRMATION #############################


@app.route('/signup-confirmation')
def signup_confirmation():
	return render_template(
		'confirmation.html',
		titleAboveSVG="Thanks for signing up!",
		svg="checkmark",
		titleBelowSVG="You will receive a confirmation email in a few minutes."
	)



#################################### TOPUP #####################################


@app.route('/topup', methods=['GET','POST'])
@app.route('/commit', methods=['GET','POST'])
def topup():
	# check if user is a parameter in URL and the hash is valid
	if not('user' in request.args and unhashID(request.args['user']) >= 0):
		return render_template(
			"confirmation.html",
			titleAboveSVG="Invalid URL",
			svg="file-alert",
			titleBelowSVG="Did you use the link we emailed you?"
		)
	airtable = Airtable("Participants")
	# check if ID is in database
	if not airtable.match('ID', unhashID(request.args['user'])):
		return render_template(
			"confirmation.html",
			titleAboveSVG="Member not found",
			svg="file-alert",
			titleBelowSVG="Did you use the link we emailed you?"
		)

	if request.method == "GET":
		return render_template(
			"topup.html",
			userHash=request.args['user'],
			nextWeekRange=getWeekToCommitToRange(),
			dayOptions=getCommitDayOptions()
		)
	else: # POST
		airtable.update_by_field(
			"ID",
			unhashID(request.args['user']),
			{"Day Preference": list(dict(request.form).keys())}
		)
		return redirect('/commit-confirmation')


############################## TOPUP CONFIRMATION ##############################


@app.route('/commit-confirmation')
def commit_confirmation():
	return render_template(
		'confirmation.html',
		titleAboveSVG="You're all set for this week!",
		svg="checkmark",
		titleBelowSVG="You can close this tab."
	)


################################### FEEDBACK ###################################


@app.route('/feedback', methods=['GET', 'POST'])
def feedback():
	# check if user is a parameter in URL and the hash is valid
	if not('user' in request.args and unhashID(request.args['user']) >= 0):
		return render_template(
			"confirmation.html",
			titleAboveSVG="Invalid URL",
			svg="file-alert",
			titleBelowSVG="Did you use the link we emailed you?"
		)
	airtableParticipants = Airtable("Participants")
	# get dict of participants
	participants = {
		record['fields']['ID'] : record['fields'] for record in airtableParticipants.get_all()
	}
	# check if ID is in database
	if unhashID(request.args['user']) not in participants:
		return render_template(
			"confirmation.html",
			titleAboveSVG="Member not found",
			svg="file-alert",
			titleBelowSVG="Did you use the link we emailed you?"
		)


	if request.method == "GET":
		# get user's pairs
		# list them all with 3 buttons for each for feedback (all optional)
		# list all people that are assigned to them with 3 butons for feedback (all optional)
		# submit on airtable
		airtablePairs = Airtable('Emails')
		# get list of participants
		# make it include every row the id matches on Emails table #############
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
		recordsToUpdate = {}
		for feedback in dict(request.form).keys():
			id = 								int(feedback.split("-")[1])
			feedbackCategory = 	feedback.split("-")[0]
			feedbackCount = 		participants[id][feedbackCategory] + 1

			if id in recordsToUpdate:
				recordsToUpdate[id][feedbackCategory] = feedbackCount
			else:
				recordsToUpdate[id] = {feedbackCategory: feedbackCount}

		airtableParticipants.batch_update_by_field("ID", recordsToUpdate)

		return redirect("/feedback-confirmation")


############################ FEEDBACK CONFIRMATION #############################


@app.route('/feedback-confirmation')
def feedback_confirmation():
	return render_template(
		'confirmation.html',
		titleAboveSVG="Thanks for your feedback!",
		svg="checkmark",
		titleBelowSVG="You can close this tab."
	)


################################# VIEW EMAILS ##################################


# add commit email route
if DEBUG_MODE:
	@app.route('/signup-email')
	def viewSignupEmail():
		airtableParticipants = Airtable("Participants")
		participants = {
			row['fields']['ID'] : row['fields'] for row in airtableParticipants.get_all(
				fields=[
					'ID','Name','Email','LinkedIn Profile','Day Preference','Time Zone','Group'
				]
			)
		}
		return render_template(
			"emails/signup.html",
			name="Scott Spiderman",
			group="Sandbox",
			userHash=hashID(114)
		)


	@app.route('/profiles-email')
	def viewWeeklyEmail():
		airtableParticipants = Airtable("Participants")
		participants = {
			row['fields']['ID'] : row['fields'] for row in airtableParticipants.get_all(
				fields=[
					'ID','Name','Email','LinkedIn Profile','Day Preference','Time Zone','Group'
				]
			)
		}

		return render_template(
			"emails/profiles.html",
			name="Scott Spiderman",
			userHash=hashID(114),
			peopleToCommentOn=[110,111,112],
			peopleThatWillComment=[120,121,122],
			participants=participants,
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
