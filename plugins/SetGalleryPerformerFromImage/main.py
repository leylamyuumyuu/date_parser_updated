
from PythonDepManager import ensure_import
import sys
ensure_import("stashapi:stashapp-tools")
import stashapi.log as log
from stashapi.stashapp import StashInterface
import logging
import json

fh = logging.FileHandler('./logs.log',mode="w")
fh.setLevel(logging.DEBUG)
logger = logging.getLogger("StashLogger")
logger.addHandler(fh)

json_input = json.loads(sys.stdin.read())
mode_arg = json_input["args"]["mode"]
stash = StashInterface(json_input["server_connection"])


image_fragment = "{ performers { id }}"

def add_performer_from_images(galleries):
	for gallery in galleries:
		images = stash.find_gallery_images(gallery_id=gallery['id'])
		logger.info(images)
		performers = []
		for i in images:
			logger.info(i)
			performers.extend(i['performers']['id'])
		logger.info(performers)
		sys.exit(0)
	pass

def main(*args, **kwargs) -> None:
	cb = add_performer_from_images
	galleries = stash.find_galleries(filter={"per_page": 50},callback=cb)


if __name__ == "__main__":
	main()
