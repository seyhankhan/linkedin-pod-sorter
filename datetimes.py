from datetime import datetime, timedelta, date, time
from pytz import common_timezones, timezone


""" common_timezones """
def getAllTimezones():
	return common_timezones


""" timezone, datetime """
def getCurrentDatetime():
	return timezone("UTC").localize(datetime.now())


""" datetime, time, timezone """
def getCommitDeadline(date, userTimezones):
  emailDatetime = datetime.combine(date, time(7, 30))
  earliestDatetime = timezone("UTC").localize(emailDatetime)
  for userTimezone in userTimezones:
    timezoneDatetime = timezone(userTimezone).localize(emailDatetime)
    if timezoneDatetime < earliestDatetime:
      earliestDatetime = timezoneDatetime
      return earliestDatetime


""" getCurrentDatetime, timedelta """
def getCurrentCommitWeekMonday(timezones=None):
	# get the date right NOW
  # if before Friday's commit deadline:
  #     its last monday
  # if after Friday's commit deadline:
  #     its next monday
	now = getCurrentDatetime()

  friday = now.date() + timedelta(days=-now.weekday() + 4)
  if not timezones:
    timezones = [
      row['fields']['Time Zone'] for row in Airtable("Participants").get_all(
        fields=['Time Zone']
      )
    ]

  if now < getCommitDeadline(friday, timezones):
    return now.date() + timedelta(days=-now.weekday())
  else
    return now.date() + timedelta(days=-now.weekday() + 7)


""" getCurrentCommitWeekMonday, timedelta, timezone, datetime, DAYS """
def calculateEmailTimestamp(userDay, userTimezone):
	# get date of when LAST commit email was sent
	# add days to make it the Day Preference
	nextUserDay = getCurrentCommitWeekMonday() \
		+ timedelta(days=DAYS.index(userDay))

	datetimeToSend = timezone(userTimezone).localize(
		datetime.combine(nextUserDay, time(7, 30))
	)
	return int(datetimeToSend.timestamp())


""" getCurrentCommitWeekMonday, timedelta """
# 29 Dec - 2 Jan
def getWeekToCommitToRange():
	monday = getCurrentCommitWeekMonday()
	friday = monday + timedelta(days=4)
	# Add monday's month if different to friday's
	extraMonth = " %b" if monday.month != friday.month else ""
	return monday.strftime("%-d" + extraMonth) + " - " + friday.strftime("%-d %b")


""" getCurrentCommitWeekMonday, getCurrentDatetime, Airtable, timedelta, getCommitDeadline """
# list of every weekday & its full date
def getCommitDayOptions():
  timezones = [
		row['fields']['Time Zone'] for row in Airtable("Participants").get_all(
      fields=['Time Zone']
    )
	]
	monday = getCurrentCommitWeekMonday(timezones)
	now = getCurrentDatetime()

	options = []
	for i in range(5):
		weekday = monday + timedelta(days=i)
		if now < getCommitDeadline(weekday, timezones):
			options.append({
				'date'	:	weekday.strftime("%A, %-d %b"),
				'value'	:	weekday.strftime("%A")
			})
	return options
