import string
import random

def id_generator(size=20, chars=string.ascii_uppercase + string.digits):
	return ''.join(random.choice(chars) for _ in range(size))

print (id_generator())

