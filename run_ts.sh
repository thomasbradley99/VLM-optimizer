#!/bin/bash
cd /home/ubuntu/volleyball/VLMvolleyball
export MUTATOR_NB=$PWD/mutator/lineages/twostage
export RESULTS_STORE=$PWD/mutator/lineages/twostage/results.jsonl
python3 -u mutator/mutator.py --rounds 3 --budget 25
