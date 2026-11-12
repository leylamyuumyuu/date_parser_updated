
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
sc_l = len(json_input["server_connection"])
logger.info("="*sc_l)
logger.info(json_input["server_connection"])
logger.info("="*sc_l)

image_fragment = "{ performers { id }}"
COUNT = -1
TOTAL = 0
def add_performer_from_images(galleries, count, page_number):
	global COUNT
	global TOTAL
	if COUNT == -1:
		COUNT = count
	if COUNT == 0:
		return
	TOTAL += 1
	log.progress(TOTAL/COUNT)
	for gallery in galleries:
		images = stash.find_gallery_images(gallery_id=gallery['id'])
		logger.debug(images)
		performers = []
		for i in images:
			logger.debug(i)
			performers.extend(i['performers'])
		logger.debug(performers)
		performer_ids = [p['id'] for p in performers]
		logger.debug(performer_ids)
		if len(performers) > 0:
			stash.update_galleries(
				{
					"ids": [gallery['id']], 
					"performer_ids": { "mode": "ADD", "ids": performer_ids }
				}
			)
		#sys.exit(0)
	pass

def main(*args, **kwargs) -> None:
	cb = add_performer_from_images
	galleries = stash.find_galleries(filter={"per_page": 50, "sort":"created_at", "direction": "DESC"}, get_count=True, callback=cb)


if __name__ == "__main__":
	main()
