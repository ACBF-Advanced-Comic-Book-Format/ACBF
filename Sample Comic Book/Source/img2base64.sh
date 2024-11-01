#!/bin/bash

: > output.txt

for file in *.jpg;
do
	#add opening tag
	echo " <binary id=\"$file\" content-type=\"image/jpg\">" >> output.txt
	#add base64
	base64 "$file" >> output.txt
	#add closing tag
	echo "</binary>" >> output.txt
done
