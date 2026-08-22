#!/bin/bash
# Two blind lineages, one after the other. Sequential on purpose: two mutator processes at
# concurrency 24 would put 48 calls in flight and trip the rate limiter, and a throttled clip
# returns nothing -- indistinguishable from a config that destroyed recall.
cd /home/ubuntu/volleyball/VLMvolleyball
for L in terse6s verbose15; do
  echo "════════════════════ LINEAGE $L ════════════════════"
  MUTATOR_NB=$PWD/mutator/lineages/$L \
  RESULTS_STORE=$PWD/mutator/lineages/$L/results.jsonl \
  python3 -u mutator/mutator.py --rounds 8 --budget 45
done
echo "════════════════════ BOTH DONE ════════════════════"
