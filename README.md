Quick and dirty script to process attendee lists from Expectnation.

## Install

It's just available here for now.

```bash
# Probably use sudo
$ pip install git+https://github.com/eremedia/attendee-list-processor
```

## Use

```bash
$ process_attendee_list
```

## Notes

* The source file *must* be a CSV file with the following headers:
  - first_name
  - last_name
  - email
  - affiliation (i.e. company)
  - position (i.e. job title)
  - phone
* Fields can be prefixed with "user." but otherwise should have those exact names (any order is fine).
* All fields are required on the file, but data is not required for them in each row. (Except for first name and last name; these *are* required for every row.)
