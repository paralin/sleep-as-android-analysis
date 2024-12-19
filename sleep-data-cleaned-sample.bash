#!/bin/bash

exec jq '[ .[0:10][] ]' sleep-data-cleaned.json > sleep-data-cleaned-sample.json
