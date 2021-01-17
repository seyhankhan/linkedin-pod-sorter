from base64 import b64decode, b64encode

def base64_to_utf8(letters):
	letters += "=" * (4 - len(letters) % 4)
	try:
		return b64decode(letters.encode('utf-8'), altchars=b'-_').decode('utf-8')
	except UnicodeDecodeError as e:
		print(e)
		return ""


def utf8_to_base64(letters):
	return b64encode(letters.encode("utf-8"), altchars=b'-_').decode("utf-8").replace("=","")


# takes integer ID, convert to string hash
def hashID(id, name=""):
	# if id not integer
	if type(id) != type(1):
		return ""
	return name.replace(" ","-").ljust(6, "_")[:6] + utf8_to_base64(str(id * 379499079)[::-1])


# takes string hash, convert to integer ID
def unhashID(idHash):
	# remove first 6 chars (name) and return -1 if hash <= 6 chars
	base64num = idHash[6:]
	if not base64num:
		return -1
	# convert base64 to utf8 and return -1 if it isnt an integer
	utf8num = base64_to_utf8(base64num)
	if not utf8num.isnumeric():
		return -2
	# reverse num to make ID, convert to int
	# return -1 if not divisible by the ID multiplier
	idBig = int(utf8num[::-1])
	if idBig % 379499079:
		return -3

	return int(idBig / 379499079)
