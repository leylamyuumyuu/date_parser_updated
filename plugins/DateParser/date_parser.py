import os
import sys, json
from PythonDepManager import ensure_import
ensure_import("dateparser>=1.2.1")
ensure_import("stashapi:stashapp-tools")
import stashapi.log as log
from stashapi.stashapp import StashInterface
import re
from dateparser import parse


def main():
    global stash
    global pattern

    json_input = json.loads(sys.stdin.read())
    mode_arg = json_input["args"]["mode"]

    stash = StashInterface(json_input["server_connection"])
    config = stash.get_configuration()["plugins"]
    settings = {"setTitle": False, "simplifiedPattern": False, "dryRun": False}
    if "date_parser" in config:
        settings.update(config["date_parser"])
    if settings.get("simplifiedPattern", False):
        # simplified pattern only matches YYYY-MM-DD
        p = r"((\d{4})[\.\-/\\](\d{1,2})[\.\-/\\](\d{1,2}))\D*"
    else:
        p = r"\D((\d{4}|\d{1,2})[\._\- /\\](\d{1,2}|[a-zA-Z]{3,}\.*)[\._\- /\\](\d{4}|\d{1,2}))\D*"
    pattern = re.compile(p)
    log.warning(f"Dry Run: {settings.get("dryRun")}")
    match mode_arg:
        case "gallery":
            find_date_for_galleries(settings)
        case "image":
            find_date_for_images(settings)
        case "scene":
            find_date_for_scenes(settings)

def parse_date_candidate(string):
    result = None
    for match in pattern.finditer(string):
        g0 = match.group(1)
        g1 = match.group(2)
        g2 = match.group(3)
        g3 = match.group(4)
        temp = parse(g1 + " " + g2 + " " + g3)
        if temp:
            potential_title = None
            _,ext = os.path.splitext(string)
            if not ext and g0 in os.path.basename(string):
                potential_title = os.path.basename(string).replace(g0, "").strip()
            result = [temp.strftime("%Y-%m-%d"), potential_title]
    return result


GALLERY_FRAGMENT = {
    "gallery":"""
    id
    title
    date
    files {
        path
    }
    folder {
        path
    }
""",
    "scene":"""
    id
    title
    date
    files {
        path
    }
""",
    "image": """
     id
    title
    date
    files {
        path
    }
"""
}

def update_item(item, acceptableDate, settings):
    log.info(
        "Gallery ID ("
        + item.get("id")
        + ") has matched the date : "
        + acceptableDate[0]
    )
    updateObject = {"id": item.get("id"), "date": acceptableDate[0]}
    if settings['setTitle'] and not item.get("title") and acceptableDate[1]:
        updateObject["title"] = acceptableDate[1]
    return updateObject

def check_files(item):
    acceptableDate = None
    for file in item.get("files", []):
        file_path = file.get("path", "")
        if file_path:
            log.debug(f"Checking file path: {file_path}")
            if candidate := parse_date_candidate(file_path):
                acceptableDate = candidate
    return acceptableDate

def check_folders(item, **kwargs):
    item_type = kwargs.get("item_type", "Item")

    acceptableDate = None
    if "folder" in item and item["folder"]:
        folder_path = item["folder"].get("path", "")
        if folder_path:
            if candidate := parse_date_candidate(folder_path):
                acceptableDate = candidate
        else:
            log.debug(f"{item_type or 'gallery'} ID {item.get('id')} has a folder entry but no path")
    return acceptableDate

def process_item(item, update_function, settings, folder=False, **kwargs):
    item_type = kwargs.get("item_type", "Item")
    acceptableDate = None
    acceptableDate = check_files(item)
    if folder:
      acceptableDate = check_folders(item, item_type=item_type) or acceptableDate
    if acceptableDate:
        updateObject = update_item(item, acceptableDate, settings)
        if not settings["dryRun"]:
            update_function(updateObject)
        else:
            log.info(f"{item_type} ID ({item.get('id')}) - date found ({acceptableDate}), not updating (dry run)")
    else:
        log.debug(f"{item_type} ID ({item.get('id')}) - no date found in paths")


def find_date_for_images(settings):
    page = 0
    total = -1
    # loop through page to avoid load on server/client
    image_count, _ = stash.find_images(f={"is_missing": "date"}, filter = {"per_page": 500, "page":page}, get_count=True)
    log.info(f"Found {image_count} images")
    while total != 0:
        images = stash.find_images(f={"is_missing": "date"}, filter = {"per_page": 500, "page":page}, fragment=GALLERY_FRAGMENT['image'])
        total = len(images)
        log.info(f"This page has {total} images.")
        for i, image in enumerate(images):
            log.progress(i / total)
            process_item(image, stash.update_image, settings,  item_type="image")
        page += 1
    return

def find_date_for_scenes(settings):
    page = 0
    total = -1
    # loop through page to avoid load on server/client
    image_count, _ = stash.find_images(f={"is_missing": "date"}, filter = {"per_page": 500, "page":page}, get_count=True)
    log.info(f"Found {image_count} scenes")
    while total != 0:
        scenes = stash.find_scenes(f={"is_missing": "date"}, filter = {"per_page": 500, "page":page}, fragment=GALLERY_FRAGMENT['scene'])
        total = len(scenes)
        log.info(f"Found {total} scenes")
        for i, scene in enumerate(scenes):
            log.progress(i / total)
            process_item(scene, stash.update_scene, settings, item_type="Scene")
        page += 1
    return



def find_date_for_galleries(settings):
    galleries = stash.find_galleries(f={"is_missing": "date"}, fragment=GALLERY_FRAGMENT['gallery'])
    total = len(galleries)
    log.info(f"Found {total} galleries")
    for i, gallery in enumerate(galleries):
        log.progress(i / total)
        process_item(gallery, stash.update_gallery, settings, True, item_type="Gallery")


if __name__ == "__main__":
    main()
