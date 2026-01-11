import os
import re
import sys
sys.path.append("../../src")
from util import *

def prune_header_sv():
    """
    Prune the header.sv file to only include PL annotations of reachable ones
    """

    # header_ia.sv assumes that all instructions will be committed, this is faulty and we need to change it
    # Need to check for squash
    header_sv = "../header_ia.sv"
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
        out_f.write("wire left_perf_locs = !in_perf_locs;\n")

        out_f.write("\n")

def generate_spv_check(name, from_signal, to_signal, from_precond=None, to_precond=None, keep_driving_logic=False):
    """
    Generates the SPV check for a given name, from_signal, to_signal, from_precond, to_precond
    Returns the string of that SPV check
    """

    spv_check = f"check_spv -create -name {{{name}}} -from {{{from_signal}}} -to {{{to_signal}}}"

    if from_precond:
        spv_check += f" -from_precond {{{from_precond}}}"

    if to_precond:
        spv_check += f" -to_precond {{{to_precond}}}"

    if keep_driving_logic:
        spv_check += " -keep_driving_logic"

    return spv_check

def obtain_opcodes():
    """
    Generates a dictionary of all of the opcodes from the opcodes_gen_all directory
    Key will be the name instruction (found in file name) and value will be a list of all the opcode portions extracted from the file
    """

    directory = "../../opcodes_gen_all"

    opcodes = {}

    # Get all files in the directory
    for filename in os.listdir(directory):
        # TODO: may want to get rid of specific extensions
        if filename.endswith('.sv') or filename.endswith('.v'):
            # Extract instruction name from filename (remove extension)
            instruction_name = os.path.splitext(filename)[0]
            
            # Read the file and extract opcode portions
            filepath = os.path.join(directory, filename)
            opcode_portions = []
            
            with open(filepath, 'r') as f:
                for line in f:
                    line = line.strip()
                    # Skip empty lines and define directives
                    if not line or line.startswith('`define'):
                        continue
                    
                    # Extract the opcode portion from assume property statements
                    # Pattern: i_INSTRUCTIONNAME_N: assume property (i0[bits] == value);
                    # We want to extract: i0[bits] == value
                    match = re.search(r'assume property\s*\((.*?)\);', line)
                    if match:
                        opcode_portion = match.group(1).strip()
                        opcode_portions.append(opcode_portion)
            
            # Store in dictionary
            opcodes[instruction_name] = opcode_portions
    
    return opcodes

def generate_spv_tcl():
    """
    Generate the SPV TCL file
    """

    template = "./squash_detect_template.tcl"
    opcodes = obtain_opcodes()
    instruction_signal = "id_stage_i.instruction"
    out = "./squash_detect.tcl"
    
    with open(out, "w") as out_f:
        # Write SPV checks
        for instruction_name, opcode_portions in opcodes.items():
            # Concatenate all opcode portions into a single precondition
            from_precond = " && ".join(opcode_portions).replace("i0", instruction_signal)

            # Append onto precondition that this instruction should not be the 
            # same as the instruction we are detecting a squash
            from_precond += " && id_stage_i.fetch_entry_i.address != pc0"

            to_precond = "left_perf_locs && $past(in_perf_locs)"

            # Add check that instruction did not commit normally
            to_precond += " && !seen_instn_committed && !instn_committed"

            spv_check = generate_spv_check(
                name=f"{instruction_name}_squasher",
                from_signal=instruction_signal,
                to_signal="left_perf_locs",
                from_precond=from_precond,
                to_precond=to_precond,
                keep_driving_logic=False # TODO check if we need, this makes slower
            )

            out_f.write(spv_check)
            out_f.write("\n")

        out_f.write("\n")

        # Read template content
        with open(template, "r") as f:
            template_content = f.read()

        # Append template content
        out_f.write(template_content)

if __name__ == "__main__":
    # Prune header.sv
    prune_header_sv()

    # Generate Top File
    generate_spv_signals()

    # Generate SPV Checks
    generate_spv_tcl()
