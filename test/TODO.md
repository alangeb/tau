Use your testsuite skill. Then locate and read testcase 10.0.2 ( test/tc_10.0.2_a2a_basic.sh ). Consider the way we are testing there a template, feel free to improve on this, but a test should use a2a the way we are doing it there, spawn one agent, then execute a series of tests. then cleanup.

Following this example create a series of new complete complex testcases (testsuite testcases). ensure all of them can execute fast.

tc_10.0.3_a2a_basic_tools (DONE)
tc_10.0.4_run_background_vi (DONE)
tc_10.0.5_run_background_nano (DONE)
tc_10.0.6_programming (DONE)
tc_10.0.7_a2a_context_management (DONE)
tc_10.0.8_a2a_subagent_fork (DONE)
tc_10.0.9_a2a_commands (DONE)

tc_10.1.0_a2a_multistep (TODO)
Test complex multi-step workflows requiring multiple interactions with the agent.

Implement these tests. Fully debug these tests. If something fails, assume the problem is in your testcases, not the agent.

Iterate on this, don't stop until you are fully done.
