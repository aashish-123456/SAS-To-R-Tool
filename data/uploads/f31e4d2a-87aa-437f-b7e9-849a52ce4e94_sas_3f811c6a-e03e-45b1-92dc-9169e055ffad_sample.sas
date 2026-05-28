data test;
input x y;
datalines;
1 2
3 4
;
run;
proc means data=test;
var x;
run;