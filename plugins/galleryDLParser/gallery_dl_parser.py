import os
import sys, json
from PythonDepManager import ensure_import
ensure_import("dateparser>=1.2.1")
ensure_import("stashapi:stashapp-tools")
import stashapi.log as log
from stashapi.stashapp import StashInterface
import re
import requests
from datetime import datetime
from dateparser import parse

title_fields = [
	"title"
]
date_fields = [
	"date",
	"created_at",
	"updated_at",
	"createTime",
	"created"
	"post_date",
	"date_url",
	"media_asset.created_at",
	"media_asset.updated_at"
]
details_fields = [
	"description"
]
urls_fields = [
	"url",
	"urls",
	"post_url",
	"file_url",
	"large_file_url",
	"preview_file_url",
	
]

performer_fields = [
	"user",
	"username",
	"fullname",
	"tags_cosplayer",
	"userName",
	"tagged_users",
	"model_name",
	"tags_character",
	"author.uniqueId",
	"author.nickname",
	"author"
]
group_fields = [
	"group"
]
studio_fields = [
	"category"
]

photographer_fields = [
	"tags_artist"
]

tags_fields = [
	"tags",
	"niches",
	"categories"
]

custom_fields = {
	"artist": [
		"tags_artist"
	],
	"copyright": [
		"tags_copyright"
	],
	"source": "category",
	"sexuality": "sexuality"
}


json_input = json.loads(sys.stdin.read())
mode_arg = json_input["args"]["mode"]
stash = StashInterface(json_input["server_connection"])

def process_performer(performers):
	log.debug("Running process performer.")
	return [stash.find_performer(perf, True).get("id") for perf in performers]
	for performer in performers:
		# check if performer exists 
		# name, alias, disambiguation
		exists = True
		if exists:
			# get performer id, 
			pass
		else:
			# create performer, get id
			pass
		# add performer to image/scene

def process_tags(tags):
	log.debug("Running process tags.")
	return [stash.find_tag(tag, True).get("id") for tag in tags]
	for tag in tags:
		stash_tag = stash.find_tag(tag, True)
		# check if tag exists 
		exists = True
		if exists:
			# get tag id, 
			pass
		else:
			# create tag, get id
			pass
		# add tag to image/scene

def process_dates(dates):
	valid_dates = []
	for d in dates:
		dt_object = None
		if isinstance(d, int):
			dt_object = datetime.fromtimestamp(d)
		if isinstance(d, str):
			dt_object = parse(d)

		if dt_object:
			d = dt_object.strftime('%Y-%m-%d')
			valid_dates.append(d)
		pass
	return valid_dates

def process_group(groups):
	# this isn't a priority
	return groups


FIELDS = [
	{"output_field": "title", "input_fields": title_fields, "choose": "first"},
	{"output_field": "date", "input_fields": date_fields, "choose": "first", "processing": process_dates},
	{"output_field": "details", "input_fields": details_fields, "choose": "all", "processing":"\n\n\n".join},
	{"output_field": "urls", "input_fields": urls_fields, "choose": "all"},
	{"output_field": "performer", "input_fields": performer_fields, "choose": "all", "processing": process_performer},
	# {"output_field": "group", "input_fields": group_fields, "choose": "first", "processing": process_group},
	{"output_field": "studio", "input_fields": studio_fields, "choose": "first"},
	{"output_field": "photographer", "input_fields": photographer_fields, "choose": "first"},
	{"output_field": "tags", "input_fields": tags_fields, "choose": "all"},
]

IMAGE_QUERY = """
	id
	title
	date
	custom_fields
	files {	
		path	
	}
"""

SCENE_QUERY = """
	id
	title
	date
	custom_fields
	files {
			path
	}
"""
TOTAL = 0
processAll = False
def load(filepath):
	try:
		with open(filepath) as fp:
			log.info(f"found: {filepath}")
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

def get_images(f = {}, filter = {}):
	page = 0
	total = -1
	g = {"per_page": 500, "sort":"created_at", "direction": "DESC"}
	g.update(filter)
	while total != 0:
		g.update({"page": page})
		total, images = stash.find_images(f, g, fragment=IMAGE_QUERY, get_count=True)
		for i in images:
			log.debug(i['custom_fields'])
			findAll = cascade_get(i, "custom_fields.gdl_found")
			if processAll and not findAll:
				continue
			yield i
		page += 1
def get_scenes(f = {}, filter = {}):
	page = 0
	total = -1
	g = {"per_page": 500, "sort":"created_at", "direction": "DESC"}
	g.update(filter)
	while total != 0:
		g.update({"page": page})
		total, images = stash.find_scenes(f, g, fragment=IMAGE_QUERY, get_count=True)
		for i in images:
			yield i
		page += 1
	

def get_files(*args, **kwargs):
	for i in get_scenes(*args, **kwargs):
		yield i
	for i in get_images(*args, **kwargs):
		yield i
	pass

def cascade_get(dictionary, key: str, default = None):
	top, *rest = key.split(".", 1)
	top_result = dictionary.get(top)
	if top_result == None:
		return default
	if len(rest) == 0:
		return top_result
	return cascade_get(top_result, rest[0], default)

def process_image(image, dryRun = False):
	data = open_json_file(image)
	

	update_input = {"id": image['id'], "custom_fields": {"partial": {}}}
	updated = False
	found = len(data) > 0
	if found:
		log.info("data found")
		# log.info(data)
		for field in FIELDS:
			log.debug(field.get("output_field"))
			choose = field.get("choose")
			choices = []
			input_fields = field.get("input_fields", [])
			log.debug(input_fields)
			for d in data:
				for f in input_fields:
					if o:=cascade_get(d,f):
						choices.append(o)
			# log.debug("choices before filtering")
			# log.debug(choices)
			if len(choices) > 0:
				log.info(f"Found choices: {choices}")
				# field.get("process", lambda x: x)(choices)
				if c:=field.get("processing"):
					log.warning(f"Running processing script on choices for field {field}.")
					choices = c(choices)
					choices = [c for c in choices if c]
				if choose == "first":
					choices = choices[0]
			else:
				continue
			log.debug("choices after filtering")
			log.debug(choices)
			if choices:
				update_input[field['output_field']] = choices
				updated = True
	update_input['custom_fields']['partial']['gdl_found'] = int(found)
	update_input['custom_fields']['partial']['gdl_checked'] = int(True)
	update_input['custom_fields']['partial']['gdl_updated'] = int(updated)
	if not dryRun or not found:
		log.info("Updating image")
		log.debug(update_input)
		stash.update_image(update_input)
	else:
		log.info(update_input)

def main():
	config = stash.get_configuration()["plugins"]
	settings = {"dryRun": False}
	files = []
	settings.update(config.get("gallery_dl_parser", {}))
	dryRun = settings.get("dryRun", False)
	log.warning(f"Dry Run: {dryRun}")
	f = {}
	processAll = settings.get("processAll", False)
	match mode_arg:
		case "image":
			files = get_images(f)
		case "scene":
			files = get_scenes(f)
		case _:
			files = get_files(f)
			pass
	
	for file in files:
		process_image(file, dryRun)
		# break


if __name__=="__main__":
	main()