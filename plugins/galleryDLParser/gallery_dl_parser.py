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
import sys
import logging
from utils import *
fh = logging.FileHandler('./logs.log',mode="w")
fh.setLevel(logging.DEBUG)
logger = logging.getLogger("StashLogger")
logger.addHandler(fh)

title_fields = [
	"title"
]
date_fields = [
	"date",
	"created_at",
	"updated_at",
	"createTime",
	"created",
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
	"user.name",
	"username",
	"fullname",
	"tags_cosplayer",
	"userName",
	"tagged_users.*.username",
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

dryRun = False
CONSERVATIVE_MODE = False
overwrite = False
def _find_performer(perf):
	log.debug(f"perf: {perf}")
	try:
		p = stash.find_performer({"name": perf}, True)
		log.debug(f"found performer: {p}")
		return p
	except:
		logger.exception(f"Error occurred processing performer {perf}")
		con_check()
		return {}

def process_performer(performers):
	log.debug("Running process performer.")
	return [_find_performer(perf).get("id", None) for perf in performers]

def _process_tag(tag):
	try:
		return stash.find_tag(tag, True)
	except:
		logger.exception(f"Error occurred processing tag: {tag}")
		con_check()
		return {}

def process_tags(tags):
	log.debug(f"Running process tags: {tags}")
	o = [_process_tag(tag) for tag in tags]
	log.debug(f"final tags: {o}")
	return [i.get("id") for i in o]

def process_dates(dates):
	logger.debug("Processing dates")
	logger.debug(dates)
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

def process_url(url) -> str | list[str]:
	log.debug(f"Processing url: {url}")
	if isinstance(url, list):
		log.warning("List passed to process_url.")
		return url # this should never happen
	if isinstance(url, dict):
		return [str(v) for v in url.values()]
	return str(url)
	
def process_urls(urls) -> list[str]:
	log.debug(f"Processing urls: {urls}")
	output_urls:list[str] = []
	for u in urls:
		_u = process_url(u)
		if isinstance(_u, list):
			output_urls.extend(u)
		else:
			output_urls.append(u)
	return output_urls

FIELDS = [
	{"output_field": "title", "input_fields": title_fields, "choose": "first"},
	{"output_field": "date", "input_fields": date_fields, "choose": "min", "processing": process_dates},
	{"output_field": "details", "input_fields": details_fields, "choose": "all", "processing":"\n\n\n".join},
	{"output_field": "urls", "input_fields": urls_fields, "choose": "all", "processing": process_urls, "unique": True},
	{"output_field": "performer_ids", "input_fields": performer_fields, "choose": "all", "processing": process_performer},
	# {"output_field": "group", "input_fields": group_fields, "choose": "first", "processing": process_group},
	# {"output_field": "studio", "input_fields": studio_fields, "choose": "first"},
	# {"output_field": "photographer", "input_fields": photographer_fields, "choose": "first"},
	{"output_field": "tag_ids", "input_fields": tags_fields, "choose": "all", "processing": process_tags},
]

ERROR_FIELD = {
	'custom_fields': {'partial':{'gdl_error':1, "gdl_checked": 1}}
}

IMAGE_QUERY = """
	id
	title
	date
	details
	organized
	performers {
		id
	}
	urls
	tags {
		id
	}
	title
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


def get_images(f = {}, filter = {}):
	g = {"per_page": 500, "sort":"created_at", "direction": "DESC"}
	g.update(filter)
	stash.find_images(f, g, fragment=IMAGE_QUERY, get_count=True, callback=process_image_page)

def get_scenes(f = {}, filter = {}):
	g = {"per_page": 500, "sort":"created_at", "direction": "DESC"}
	g.update(filter)
	stash.find_scenes(f, g, fragment=IMAGE_QUERY, get_count=True, callback=process_scene_page)

def con_check():
	if CONSERVATIVE_MODE:
		logger.info("Conservative mode: true. Exiting.")
		import sys
		sys.exit(1)

def update_progress(count):
	global TOTAL
	log.progress(TOTAL/max(count, 1))
	TOTAL += 1

def process_scene_page(items, count, page_number, **kwargs):
	logger.info(f"Total scenes: {count}.")
	logger.info(f"Processing scene page: {page_number}.")
	logger.info(count)
	logger.info(kwargs)
	for i in items:
		update_progress(kwargs.get("count", 1))
		try:
			process_image(i, stash.update_scene)
		except Exception as e:
			logger.exception(f"An error occurred when processing the scene. {i['id']}")
			con_check()


def process_image_page(items, count, page_number, **kwargs):
	logger.info(f"Total images: {count}")
	logger.info(f"Processing image page: {page_number}.")
	logger.info(count)
	for i in items:
		update_progress(kwargs.get("count", 1))
		try:
			process_image(i)
		except Exception as e:
			# log.error(e.__traceback__)
			logger.exception(f"An error occurred when processing the image. {i['id']}")
			con_check()

def process_image(image, update_function= stash.update_image):
	data = open_json_file(image)
	p_ids = [i.get('id') for i in image['performers'] if i]
	t_ids = [i.get('id') for i in image['tags'] if i]
	log.debug(p_ids)
	log.debug(t_ids)
	# sys.exit(0)
	update_input = {"id": image['id'], "custom_fields": {"partial": {}}, "tag_ids": t_ids, "performer_ids":p_ids}
	# update_input.update(image)
	updated = False
	found = len(data) > 0
	if found:
		log.debug("data found")
		# log.info(data)
		for field in FIELDS:
			output_field = field["output_field"]
			unique = field.get("unique", False)
			log.debug(output_field)
			choose = field.get("choose")
			choices = []
			input_fields = field.get("input_fields", [])
			# log.debug(input_fields)
			for d in data:
				for f in input_fields:
					if o:=cascade_get(d,f):
						if isinstance(o, list):
							choices.extend(o)
						else:
							choices.append(o)
			log.debug(f"choices before filtering: {choices}")
			# log.debug(choices)
			if len(choices) > 0:
				log.debug(f"Found choices: {choices}")
				# field.get("process", lambda x: x)(choices)
				if c:=field.get("processing"):
					log.debug(f"Running processing script on choices for field {field}.")
					choices = c(choices)
					if isinstance(choices, list):
						choices = [c for c in choices if c]
				match choose:
					case "first":
						choices = choices[0]
					case "min":
						choices = min(choices)
					case "max":
						choices = max(choices)
			else:
				continue
			log.debug("choices after filtering")
			log.debug(choices)
			if choices:
				if isinstance(choices, list) and unique:
					choices = list(set(choices))
				if isinstance(update_input.get(output_field, None), list) and not overwrite:
					update_input[output_field].extend(choices)
				else:
					update_input[output_field] = choices

				updated = True
			log.debug(f"Successfully processed field: {output_field}")
			
	update_input['custom_fields']['partial']['gdl_found'] = int(found)
	update_input['custom_fields']['partial']['gdl_checked'] = int(True)
	update_input['custom_fields']['partial']['gdl_updated'] = int(updated)
	# update_input['custom_fields']['partial']['gdl_error'] = int(True)
	
	if not dryRun or not found:
		log.info(f"Updating image {update_input['id']}")
		log.debug(update_input)
		try:
			update_function(update_input)
		except:
			update_function(ERROR_FIELD)
	else:
		log.debug(update_input)

def main():
	global CONSERVATIVE_MODE
	config = stash.get_configuration()["plugins"]
	settings = {"dryRun": False}
	settings.update(config.get("gallery_dl_parser", {}))
	dryRun = settings.get("dryRun", False)
	CONSERVATIVE_MODE = settings.get("conservativeMode", False)
	log.warning(f"Dry Run: {dryRun}")
	f = {}
	processAll = settings.get("processAll", False)
	if not processAll:
		f["custom_fields"] = {
			"field": "gdl_checked",
			"modifier": "IS_NULL",
			"value": 0
		}
	match mode_arg:
		case "image":
			get_images(f)
		case "scene":
			get_scenes(f)
		case _:
			get_images(f)
			get_scenes(f)
	


if __name__=="__main__":
	log.warning("This is a test warning using log.")
	logger.warning("This is a test warning using logger.")
	main()