#!/bin/bash
total_lines=0

echo '   <text-layer lang="en">'

for line in `cat "$1" | grep 'd="[mM] ' | sed "s/c [0-9-]*,[0-9-]* [0-9-]*,[0-9-]* //g" | sed "s/d=\"//g" | sed "s/ z\"//g" | sed "s/^ *//g" | sed "s/ /\|/g" | sed "s/\"//g"`
do
  #echo $line
  let x_coord=0
  let y_coord=0
  points='<text-area points="'

  if [ `echo $line | cut -d '|' -f 1` = "m" ]
  then
    for tuple in `echo $line | sed "s/^m|//g" | sed "s/|/ /g"`
    do
      #echo $tuple
      x_coord="$x_coord+"`echo $tuple | cut -d ',' -f 1`
      x_coord=`echo $x_coord | bc`
      x_coord_rounded=`echo $x_coord | awk '{print int($1+0.5)}'`
      y_coord="$y_coord+"`echo $tuple | cut -d ',' -f 2`
      y_coord=`echo $y_coord | bc`
      y_coord_rounded=`echo $y_coord | awk '{print int($1+0.5)}'`
      points="$points""$x_coord_rounded"",""$y_coord_rounded "
    done
    let total_lines=$total_lines+1
  else
    for tuple in `echo $line | sed "s/^M|//g" | sed "s/|/ /g"`
    do
      #echo $tuple
      x_coord=`echo $tuple | cut -d ',' -f 1`
      x_coord_rounded=`echo $x_coord | awk '{print int($1+0.5)}'`
      y_coord=`echo $tuple | cut -d ',' -f 2`
      y_coord_rounded=`echo $y_coord | awk '{print int($1+0.5)}'`
      points="$points""$x_coord_rounded"",""$y_coord_rounded "
    done
    let total_lines=$total_lines+1
  fi
  points=`echo $points | sed "s/ $//g"`
  echo "     $points"'">'
  echo '       <p></p>'
  echo "     </text-area>"
  points='points="'
done

echo '   </text-layer>'
