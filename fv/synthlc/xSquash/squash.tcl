set RTL_DIR /home/users/wzhu17/research/SynthLC/cva6
set SRCDIR /home/users/wzhu17/research/SynthLC/cva6/core

# Initialize SPV
check_spv -init

# Read RTL + elaborate
analyze -sv09 -f squash_hdls.f -y $SRCDIR +incdir+$SRCDIR

# Black Box Frontend
elaborate -bbox_m {frontend}

# TODO REMOVE
# stopat i_frontend.fetch_entry_ready_i

# Clocks and reset
clock clk_i
reset !rst_ni

# Sanity
check_spv -create -name sanity_reachable \
  -from {flush_ctrl_if} \
  -to {id_stage_i.issue_q.valid}

# First SPV check
# TODO: check precondition assumption
# TODO: check for when it commits normally (i.e. not squash)
check_spv -create -name instn_squash \
  -from {fetch_entry_if_id.instruction[6:0]} \
  -from_precond {fetch_valid_if_id} \
  -to {left_perf_locs_curr} \
  -to_precond {left_perf_locs_rise}

puts "=== Checking SPV consistency ==="
check_spv -consistency

# Auto-abstract black boxes
check_spv -abstract -bbox_instance -mode seq

# List all SPV properties
check_spv -list properties

# Prove SPV properties
puts "=== Proving SPV properties ==="
check_spv -prove -all

# Report results
report -csv -results -file "squash_results.csv" -force

