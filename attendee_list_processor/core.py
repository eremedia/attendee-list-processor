#!/usr/bin/env python

import os, errno
import sys
import tablib
from datetime import datetime
import calendar
import phonenumbers
import urllib
import urllib2
from contextlib import closing
import time



def main():
    """Process file."""

    print ""
    print "Beginning attendee list data processing..."
    print ""
    directory = get_directory()
    print ""
    print "Please choose the export file:"
    possible_files = []
    for filename in os.listdir(directory):
        if filename.startswith(".") or filename.startswith("_"):
            continue
        if os.path.isfile(os.path.join(directory, filename)):
            possible_files.append(filename)
    for i, filename in enumerate(possible_files):
        print "[%s] %s" % (i, filename)
    print ""
    file_number_to_use = get_file_number(possible_files)
    path_to_file = os.path.join(directory, possible_files[file_number_to_use])
    print ""
    print "'%s' is the file that will be processed." % path_to_file

    print ""
    image_folder = get_image_folder(directory)
    print ""
    print "'%s' is the directory where downloaded QR codes will be stored." % image_folder

    with open(path_to_file, 'r') as f:
        data = tablib.Dataset()
        data.csv = f.read()
    attendance_types = set(data["attendance_type"])
    print ""
    print "* We found %s rows to be exported." % len(data)
    print "* We found %s attendee types: %s" % (len(attendance_types), ", ".join(attendance_types))
    print "* The following files will be created for these types:"

    export_filenames = {}
    timestamp = calendar.timegm(datetime.utcnow().utctimetuple())
    for at in attendance_types:
        export_filenames[at] = get_export_filename(directory, at, timestamp)
        print "  - %s" % export_filenames[at]


    print ""
    should_proceed = proceed("Proceed? [Enter 'y' or 'n']: ")


    # Trim "user." from front of any header fields"
    cleaned_headers = [h.replace("user.", "", 1) for h in data.headers]
    data.headers = cleaned_headers

    # Build processed data file
    processed_data = tablib.Dataset()
    processed_data.headers = ["first_name", "last_name", "affiliation", "position", "@qrcode"]

    # Create image folder if not already created
    print ""
    print "Creating folder for QR codes ('%s')..." % image_folder
    mkdir_p(image_folder)

    print ""
    for row in data.dict:
        try:
            cleaned_phone, extension = get_parsed_phone_number(row['phone'])
        except ValueError:
            cleaned_phone = get_parsed_phone_number(row['phone'])
            extension = None
        first_name = row["first_name"].strip()
        last_name = row["last_name"].strip()
        email = row["email"].strip()
        org = row["affiliation"].strip()
        title = row["position"].strip()

        vcard = get_vcard(first_name=first_name,
                          last_name=last_name,
                          email=email,
                          org=org,
                          title=title,
                          tel=cleaned_phone,
                          extension=extension)

        qr_code_url = get_qr_code_url(vcard)
        local_qr_code_path = get_qr_code_local_filepath(download_dir=image_folder,
                                                        email=email)

        # Download the file from Google Charts
        print "Downloading QR code for %s %s..." % (first_name, last_name)
        #download_remote_url_to_local_filepath(remote_url=qr_code_url, local_dest=local_qr_code_path)

        ## Sleep a bit so we don't get banned
        #time.sleep(.1)

        processed_data.rpush([
            first_name,
            last_name,
            org,
            title,
            local_qr_code_path
        ], tags=[row["attendance_type"]])

    processed_data = processed_data.sort("last_name")
    print ""
    print "All QR codes downloaded!"

    # Create files
    print ""
    print "Creating data merge files..."
    print ""
    for at in attendance_types:
        with open(export_filenames[at], "wb") as f:
            f.write(processed_data.filter([at]).csv)
        print "'%s' created." % export_filenames[at]

    print ""
    print "Attendee data processing complete!"


def get_export_filename(directory, attendance_type, timestamp):
    return "%s/processed-attendees-%s.%s.csv" % (directory, attendance_type, timestamp)


def get_directory():
    # First get the directory
    while True:
        user_input = raw_input("Enter the directory where exported data file is located [~/Desktop]: ") or "~/Desktop"
        directory = user_input.rstrip("/")
        if "~" in directory:
            home = os.path.expanduser("~")
            directory = directory.replace("~", home)
        if os.path.isdir(directory):
            return directory
        print "'%s' is not a valid directory on this system. Please try again." % user_input


def get_file_number(possible_files):
    while True:
        max_file_number = len(possible_files) - 1
        user_input = raw_input("Type the number [0-%s] that corresponds with the file you want to use (e.g. 2): " % max_file_number)
        if user_input != "":
            file_number = user_input
            try:
                file_number = int(file_number)
            except ValueError:
                print "'%s' is not a valid number. Try again." % user_input
                continue
            if file_number > max_file_number:
                print "Valid values are [0-%s]. You entered %s. Please try again." % (max_file_number, user_input)
                continue
            return file_number

def proceed(msg):
    while True:
        user_input = raw_input(msg)
        if user_input == 'y':
            return True
        if user_input == 'n':
            print "Operation cancelled by user."
            sys.exit()
        print "Invalid input. Please enter 'y' or 'n'."

def get_image_folder(directory):
    # First get the directory
    while True:
        default_directory = "%s/qr-codes" % directory
        user_input = raw_input("Enter the directory where you wish to put downloaded QR code images: [%s]" % default_directory) or default_directory
        download_directory = user_input.rstrip("/")
        if "~" in download_directory:
            home = os.path.expanduser("~")
            download_directory = download_directory.replace("~", home)
        if os.path.isdir(download_directory):
            proceed("'%s' already exists. Files may be overwritten. Proceed? [Enter 'y' or 'n']" % user_input)
        return download_directory

def get_parsed_phone_number(raw_phone_number):
    raw_phone_number = raw_phone_number.strip()
    if not raw_phone_number:
        return ""
    try:
        parsed_number = phonenumbers.parse(raw_phone_number, region="US")
        if not phonenumbers.is_possible_number(parsed_number):
            parsed_number = phonenumbers.parse(raw_phone_number)
            if not phonenumbers.is_valid_number(parsed_number):
                return ""
    except phonenumbers.NumberParseException:
        return ""

    formatted_number = phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.E164)

    # N.B. Returns a tuple if there's an extension, else a string
    if parsed_number.extension:
        return (formatted_number, parsed_number.extension)
    else:
        return formatted_number

def get_vcard(first_name, last_name, email="", org="", title="", tel="", extension=""):
    if not first_name and last_name:
        return None
    lines = [
        "BEGIN:VCARD",
        "VERSION:3.0",
        "N:%s;%s" % (last_name, first_name),
        "FN:%s %s" % (first_name, last_name),
    ]
    if org:
        lines.append("ORG:%s" % org)
    if title:
        lines.append("TITLE:%s" % title)
    if tel:
        lines.append("TEL;TYPE=WORK,VOICE:%s" % tel)
    if email:
        lines.append("EMAIL;TYPE=WORK,INTERNET:%s" % email)
    if extension:
        lines.append("NOTE:ext. %s" % extension)

    lines.append("END:VCARD")
    return "\n".join(lines)

def get_qr_code_url(msg, size="500"):
    return "http://chart.apis.google.com/chart?cht=qr&chs=%sx%s&chl=%s&chld=H|0" % (size,
                                                                                    size,
                                                                                    urllib.quote_plus(msg))

def get_qr_code_local_filepath(download_dir, email):
    return "%s/%s.png" % (download_dir, email)


def download_remote_url_to_local_filepath(remote_url, local_dest, binary=True):
    mode = 'w%s' % 'b' if binary else ''
    with closing(urllib2.urlopen(remote_url)) as remote_f:
         with open(local_dest, mode) as local_f:
             local_f.write(remote_f.read())


def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc: # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else: raise

if __name__ == '__main__':
    sys.exit(main())

