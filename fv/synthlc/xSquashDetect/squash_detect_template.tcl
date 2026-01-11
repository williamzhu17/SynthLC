puts "=== Checking SPV consistency ==="
check_spv -consistency

# Auto-abstract black boxes
check_spv -abstract -bbox_instance -mode seq

# List all SPV properties
check_spv -list properties

# Prove SPV properties
puts "=== Proving SPV properties ==="
set_spv_show_bound_progress_in_log true
check_spv -prove -all

# Report results
report -csv -results -file "squash_detect_results.csv" -force
