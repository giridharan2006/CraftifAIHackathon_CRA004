SYNTHETIC EVIDENCE - not model output, not PipeGen, not a camera.

Every detection here comes from scripts/make_synthetic_metadata.py (hand-written,
deterministic). It verifies the incident-processing component only. Generated on the
target laptop on 2026-10-16.

metadata_synthetic.jsonl        input: 80 frames; track 1 enters the zone, track 2 stays out, forklift inside
incidents_synthetic.jsonl       output: 1 incident (track 1, frame 51)
stats_synthetic.json            output statistics
demo_output.txt                 console output of scripts/run_synthetic_demo.sh
verification_output.txt         scripts/verify_synthetic_demo.py: 16/16 independent checks
mqtt_smoke_test_output.txt      scripts/mqtt_smoke_test.sh against a local Mosquitto 2.0.18 broker
mqtt_subscriber_received.txt    the message as received by an independent mosquitto_sub
run_pipeline_plumbing/          first-session run of scripts/run_pipeline.sh with a STUB in place
                                of the PipeGen run.sh (now covered by tests/test_run_pipeline.py)
