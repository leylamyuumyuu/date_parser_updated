import json
import logging

logger = logging.getLogger("utils")

def cascade_get(dictionary, key: str, default = None):
	if isinstance(dictionary, str):
		logger.debug(f"dictionary is a string. returning {dictionary or default}")
		return dictionary or default
	
	top, *rest = key.split(".", 1)
	if isList:=isinstance(dictionary, list):
		logger.debug(f"dictionary is a list. (wildcard? {top =='*'})")
		logger.debug(dictionary)
	if top == "*" and isList:
		logger.debug("Encountered wildcard.")
		top_result = [
			cascade_get(c, rest[0], default) for c in dictionary
		]
		return top_result
	else:
		top_result = dictionary.get(top) # type: ignore
	if top_result == None:
		return default
	if len(rest) == 0:
		return top_result
	return cascade_get(top_result, rest[0], default)

def load(filepath):
	try:
		with open(file=filepath) as fp:
			logger.debug(f"found: {filepath}")
			return json.load(fp)
	except:
		return None

def open_json_file(image):
	files = image['files']
	data = [
		load(file.get("path") + ".json") for file in files
	]
	data = [d for d in data if d]
	return data

if __name__ == "__main__":
	logging.basicConfig(level=logging.DEBUG, format='%(relativeCreated)6d %(threadName)s %(message)s')
	test_dict = {
		"tagged_users": [
			{"username": "test1", "user": {"name": "test1"}},
			{"username": "test2", "user": {"name": "test2"}},
			{"username": "test3", "user": {"name": "test3"}},
			{"username": "test4", "user": {"name": "test4"}},
			{"username": "test5", "user": {"name": "test5"}},
			{"username": "test6", "user": {"name": "test6"}},
		]
	}
	
	print(cascade_get(test_dict, "tagged_users.*.user.name"))