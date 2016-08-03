#!/usr/bin/python

import xmltodict
import os

test_results = {}

ls = os.listdir("reports")
for test_file in ls:
   fd = open(test_file, "r")
   test_run = xmltodict.parse(fd.read())
   test_results[test_file] = test_run

for res in test_results:
   print res
   if int(test_results[res]['testsuite']['@tests']) == 0:
      print "\tThere are no tests in this test suite."
   elif int(test_results[res]['testsuite']['@tests']) == 1:
      print "\t%(@name)s(%(@time)s secs): %(@status)s" % test_results[res]['testsuite']['testcase']
   else:
      for i in range(int(test_results[res]['testsuite']['@tests'])):
         print "\t%(@name)s(%(@time)s secs): %(@status)s" % test_results[res]['testsuite']['testcase'][i]
