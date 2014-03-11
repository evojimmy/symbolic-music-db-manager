Symbolic music database manager.

Originally for singing voice synthesis project.

For easy management of score files in Lilypond.

## Usage

````
manage.py help ACTION
manage.py list
manage.py checkout LISTFILE DESTINATION [SEPARATOR="_"]
manage.py check_integrity [ID]...
manage.py listen ID COMMAND
manage.py view   ID
manage.py export ID  [DESTINATION="$ID.pdf"]
manage.py export_all DESTINATION [KEEP_TEMP_FILES="discard"(or "keep")]
````

## Dependency

+ Python (tested on 2.7 & 3.3)
+ Lilypond (> 2.14.0 ?)
+ pdftk (tested on 1.44)

