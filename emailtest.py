# using SendGrid's Python Library
# https://github.com/sendgrid/sendgrid-python

import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from random import randint

def createEmailHTML(name, pairs):
	template = f"""
<html>
	<head>
    <meta charset="utf-8">
    <meta name="author" content="Seyhan Van Khan">
    <meta name="description" property="og:description" content="Your list of new LinkedIn profiles is here!">
    <title>Pod Sorter for LinkedIn</title>
	</head>
	<body>
		Hey{name},
		<br>
		The following participants will post on LinkedIn today - go and check out their activity
		<br>
		<br>
		""" + '<br>'.join([', '.join(pair) for pair in pairs]) + """
	</body>
</html>
	"""


def sendEmail(email='seyhan546@gmail.com'):
  randCode = str(randint(1,9999)).zfill(4)

  message = Mail(
    from_email='podlinkedin@gmail.com',
    to_emails=email,
    subject='LinkedIn Pod Sorter',
    html_content="""
      <html>
        <head>
        </head>
        <body>
          Your code is <b>""" + randCode + """</b>
        </body>
      </html>
    """
  )

  try:
    sg = SendGridAPIClient(os.environ.get('SENDGRID_KEY'))
    response = sg.send(message)
    print(response.status_code)
    print(response.body)
    print(response.headers)
  except Exception as e:
    print(e.message)

sendEmail()
