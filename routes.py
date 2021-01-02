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
button for feedback
this is low quality post/high quality post
separate groups into 2 different links
	/sandbox
	/

on emails:


"""
################################ IMPORT MODULES ################################


from base64 import b64decode, b64encode
from datetime import datetime
from json import dumps as json_dumps
from os import environ
from random import shuffle

from flask import Flask, render_template, redirect, request

from airtableEmails import *

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


##################### EMAIL ROUTE TO BE OPENED EVERY WEEK ######################


"""
Weekly Email:
Which day would you like to receive next weeks email?
 --------        ---------        -----------        ----------        --------
| Monday |      | Tuesday |      | Wednesday |      | Thursday |      | Friday |
 --------        ---------        -----------        ----------        --------

Here are your 14 profiles for this week of (21 Dec - 25 Dec):
- Steve Johnson (High Quality Post | Low Quality Post)
- etc
-
-

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
@app.route('/calculate-pairs/sunday/' + environ.get('EMAIL_CODE'), methods=['POST'])
def weeklyEmailCalculation_Sunday():
	# get all opted in from participants
	# shuffle order
	# assign max 14 IDs to each person
	# calculate UTC time to send to each

	pairs = calculateProfilePairs()
	addPairsToAirtable(pairs)
	sendWeeklyEmails(pairs)
	return redirect('/')


# covers Wednesday 00:00 UTC to Friday 23:59 UTC
# last email is sent at Friday 17:30 UTC (Hawaii)
@app.route('/calculate-pairs/wednesday/' + environ.get('EMAIL_CODE'), methods=['POST'])
def weeklyEmailCalculation_Wednesday():


	return redirect('/')


################################# OTHER ROUTES #################################


# @app.route('/<path:dummy>')
# def fallback(dummy):
# 	return redirect(url_for('index'))


#################################### APP RUN ###################################


if __name__ == "__main__":
	app.run(debug=True)
