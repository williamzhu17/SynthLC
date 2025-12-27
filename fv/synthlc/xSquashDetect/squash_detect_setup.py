import sys
sys.path.append("../../src")
from util import *

def prune_header_sv():
    """
    Prune the header.sv file to only include PL annotations of reachable ones
    """

    header_sv = "../header.sv"
    reachable_pls = get_array("../xCoverAPerflocDiv/cover_individual.txt")
    pruned_header_sv = "./reachable_pls_header.sv"

    # Convert to set for fast lookup
    reachable_pls_set = set(reachable_pls)

    with open(header_sv, "r") as f:
        lines = f.readlines()

    # Write the pruned header.sv
    pruned_lines = []
    i = 0
    in_wire_section = False
    
    # Process lines: keep everything before wires, selectively keep wires, keep everything after
    while i < len(lines):
        line = lines[i]
        
        # Check if we're entering the wire definitions section
        if "Performing location" in line:
            in_wire_section = True
            pruned_lines.append(line)
            i += 1
            continue
        
        # If we're in the wire section, process wire definitions
        if in_wire_section and line.strip().startswith("wire "):
            # Extract wire name (format: "wire <name> =")
            wire_name = line.split()[1]  # Get the name after "wire"
            # Check if this wire is in reachable_pls
            if wire_name in reachable_pls_set:
                # Include the entire wire definition (until we see 1'b1;)
                wire_block = [line]
                i += 1
                while i < len(lines) and "1'b1;" not in lines[i]:
                    wire_block.append(lines[i])
                    i += 1
                # Include the line with 1'b1;
                if i < len(lines):
                    wire_block.append(lines[i])
                pruned_lines.extend(wire_block)
            else:
                # Skip this wire definition
                i += 1
                while i < len(lines) and "1'b1;" not in lines[i]:
                    i += 1
            i += 1
        # Check if we've reached the instruction assumptions section (end of wire section)
        elif in_wire_section and line.strip().startswith("i_DIV_"):
            # Keep all instruction assumptions and everything after
            while i < len(lines):
                pruned_lines.append(lines[i])
                i += 1
            break
        # Keep all other lines (before wire section, or empty lines in wire section)
        else:
            pruned_lines.append(line)
            i += 1
    
    # Write the pruned header.sv
    os.makedirs(os.path.dirname(pruned_header_sv), exist_ok=True)
    with open(pruned_header_sv, "w") as f:
        f.writelines(pruned_lines)

def generate_spv_signals():
    """
    Generates the signals used for SPV
    """

    header = "./reachable_pls_header.sv"
    out = "./squash_detect.sv"

    reachable_pls = get_array("../xCoverAPerflocDiv/cover_individual.txt")

    with open(out, "w") as out_f:
        # Write header
        with open(header, "r") as f:
            out_f.write(f.read())

        out_f.write("\n")

        # wire in_perf_locs = PL1 || PL2 || ...;
        in_perf_locs_string = "wire in_perf_locs = " + " || ".join(reachable_pls) + ";\n"

        # Write in_perf_locs wire
        out_f.write(in_perf_locs_string)

        # Write left_perf_locs wire
        out_f.write("wire left_perf_locs = !in_perf_locs;")

        out_f.write("\n")

def generate_spv_check(name, from_signal, to_signal, from_precond=None, to_precond=None):
    spv_check = f"check_spv -create -name {{{name}}} -from {{{from_signal}}} -to {{{to_signal}}}"

    if from_precond:
        spv_check += f" -from_precond {{{from_precond}}}"

    if to_precond:
        spv_check += f" -to_precond {{{to_precond}}}"

    return spv_check

def generate_spv_tcl():
    """
    Generate the SPV TCL file
    """

    template = "./squash_detect_template.tcl"
    out = "./squash_detect.tcl"

    with open(template, "r") as f:
        template_lines = f.readlines()
    
    with open(out, "w") as out_f:
        # Write the first line: check_spv -init
        out_f.write(template_lines[0])

        out_f.write("\n")

        # Write SPV checks
        # TODO: finish generating remaining ones
        out_f.write(generate_spv_check(
            name="instn_squash",
            from_signal="fetch_entry_if_id.instruction[6:0]",
            to_signal="left_perf_locs",
            to_precond="left_perf_locs && $past(in_perf_locs)"
        ))

        out_f.write("\n")

        # Write remaining template lines
        out_f.write("".join(template_lines[1:]))

if __name__ == "__main__":
    # Prune header.sv
    prune_header_sv()

    # Generate Top File
    generate_spv_signals()

    # Generate SPV Checks
    generate_spv_tcl()
