#!/bin/bash

 go run speedtest1Min1p1Thrd.go | tee -a "GO_TEST__speedtest1Min1p1Thrd__$(date | cut -d' ' -f2-9 | sed 's/[ :]/_/g').log"
 go run speedtest1Min4p1Thrd.go | tee -a "GO_TEST__speedtest1Min4p1Thrd__$(date | cut -d' ' -f2-9 | sed 's/[ :]/_/g').log"
 go run speedtest10Min1p1Thrd.go | tee -a "GO_TEST__speedtest10Min1p1Thrd__$(date | cut -d' ' -f2-9 | sed 's/[ :]/_/g').log"
 go run speedtest10Min4p1Thrd.go | tee -a "GO_TEST__speedtest10Min4p1Thrd__$(date | cut -d' ' -f2-9 | sed 's/[ :]/_/g').log"

 grep FINAL GO_TEST__speedtest1*Min*p*Thrd__*
