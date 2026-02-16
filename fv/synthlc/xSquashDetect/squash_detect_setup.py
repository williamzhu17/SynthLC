import os
import re
import sys
sys.path.append("../../src")
from util import *

def generate_header():
    """
    Generates the header for this squash detect step
    This includes assumptions and wires that are used for the squash detect step
    """

    header = "../header_squash.sv"
    out = "./squash_detect.sv"

    reachable_pls = get_array("../xCoverAPerflocDiv/cover_individual.txt")

    with open(out, "w") as out_f:
        # Write header
        with open(header, "r") as f:
            out_f.write(f.read())

        # Extract and write i1 opcode assumptions
        # directory = "../../opcodes_gen_all"

        # # Get list of all files in the opcodes directory
        # files = os.listdir(directory)
        # matched_file = None
        # for file in files:
        #     if file == f"{i1_opcode}.sv":
        #         matched_file = os.path.join(directory, file)
        #         break
        # if not matched_file:
        #     raise ValueError(f"{i1_opcode}.sv not found in {directory}")

        # # Read the entire matched opcode file into a single string
        # with open(matched_file, "r") as f:
        #     file_contents = f.read()

        # out_f.write(file_contents.replace("i0", "i1"))

        # out_f.write("\n")

        # wire in_perf_locs = PL1 || PL2 || ...;
        # in_perf_locs_string = "wire in_perf_locs = " + " || ".join(reachable_pls) + ";\n"

        # Write in_perf_locs wire
        # out_f.write(in_perf_locs_string)

        # Write left_perf_locs wire
        # out_f.write("wire left_perf_locs = !in_perf_locs;\n")

        # out_f.write("\n")

def generate_spv_check(
    name, 
    from_signal, 
    to_signal, 
    from_precond=None, 
    to_precond=None, 
    keep_driving_logic=False,
    exclude_control_logic=False,
    not_through=None
):
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

    if exclude_control_logic:
        spv_check += " -exclude_control_logic"

    if not_through:
        spv_check += f" -not_through {{{not_through}}}"

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

def extract_operand_bits(equations, bit_width=32, prune_neq_bits=True):
    """
    Extract bit ranges UNUSED in equations: never mentioned, and optionally bits used by != (unconstrained).
    Expects equations like "i0[31:25] == 7'b0" or "i0[11:7] != 5'd0" (assume property stripped).
    Returns list of unused ranges, e.g. ["i0[24:15]", "i0[11:7]"] for the instruction.

    Args:
        equations: List of opcode equation strings.
        bit_width: Instruction bit width (default 32).
        prune_neq_bits: If True (default), bits used only in != comparisons are included as
            prunable (unused). If False, those bits are not included in the result.
    """
    pat = re.compile(r'(\w+)\[(\d+)(?::(\d+))?\]\s*(==|!=)')
    ranges_eq, ranges_neq, sig = [], [], None
    for eq in equations:
        m = pat.search(eq.strip())
        if not m:
            continue
        sig, hi_s, lo_s, op = m.groups()
        a, b = int(hi_s), int(lo_s) if lo_s else int(hi_s)
        hi, lo = max(a, b), min(a, b)  # always MSB:LSB
        (ranges_eq if op == '==' else ranges_neq).append((hi, lo))
    if not sig:
        return []

    mentioned = {b for hi, lo in ranges_eq + ranges_neq for b in range(lo, hi + 1)}
    never = set(range(bit_width)) - mentioned

    def to_ranges(bits):
        if not bits:
            return []
        s, out = sorted(bits), []
        start = end = s[0]
        for b in s[1:]:
            if b == end + 1:
                end = b
            else:
                out.append((end, start))  # MSB:LSB
                start = end = b
        out.append((end, start))  # MSB:LSB
        return out

    result = [f"{sig}[{hi}:{lo}]" for hi, lo in to_ranges(never)]
    if prune_neq_bits:
        result += [f"{sig}[{hi}:{lo}]" for hi, lo in ranges_neq]
    return sorted(result, key=lambda s: -int(re.search(r'\[(\d+)', s).group(1)))

def generate_spv_tcl():
    """
    Generate the SPV TCL file
    """

    template = "./squash_detect_template.tcl"
    instruction_signal_prefix = "id_stage_i.instruction"
    out = "./squash_detect.tcl"

    opcodes = obtain_opcodes()
    instruction_prefix = "id_stage_i.instruction"

    with open(out, "w") as out_f:
        for opcode, opcode_portions in opcodes.items():
            # if opcode != "AND" and opcode != "BNE" and opcode != "DIV" and opcode != "SW":
            #     continue

            # Operand bits of instruction
            operand_bits = extract_operand_bits(opcode_portions, prune_neq_bits=False)

            if len(operand_bits) == 0:
                continue

            from_signal = " ".join(operand_bits).replace("i0", instruction_prefix)

            # Equals a particular op
            from_precond = " && ".join(opcode_portions).replace("i0", "i1")
            from_precond += " && i1_instn_begin"

            # When we leave perf_locs abnormally
            to_signal = "left_perf_locs"
            to_precond = "!left_perf_locs && $past(in_perf_locs) && !seen_i1_committed && !i1_committed"

            # Not through these signals
            not_through = "issue_stage_i.i_issue_read_operands.rs1_i issue_stage_i.i_issue_read_operands.rs1_valid_i issue_stage_i.i_issue_read_operands.forward_rs1 issue_stage_i.i_issue_read_operands.rs2_i issue_stage_i.i_issue_read_operands.rs2_valid_i issue_stage_i.i_issue_read_operands.forward_rs2 issue_stage_i.i_issue_read_operands.rs3_i issue_stage_i.i_issue_read_operands.rs3_valid_i issue_stage_i.i_issue_read_operands.forward_rs3 issue_stage_i.i_issue_read_operands.rd_clobber_gpr_i issue_stage_i.i_issue_read_operands.rd_clobber_fpr_i issue_stage_i.i_issue_read_operands.i_ariane_regfile.waddr_i issue_stage_i.i_issue_read_operands.i_ariane_regfile.wdata_i issue_stage_i.i_issue_read_operands.i_ariane_regfile.we_i"

            # TODO not sure about these
            # not_through += " issue_stage_i.i_issue_read_operands.stall issue_stage_i.i_issue_read_operands.fu_busy"
            not_through += " no_st_pending_commit"

            # TODO: idea about not tainting the destination register
            # not_through = "issue_stage_i.wbdata_i commit_stage_i.commit_ack_o"
            # not_through = None

            spv_check = generate_spv_check(
                name=f"{opcode}_SQUASHER",
                from_signal=from_signal,
                to_signal=to_signal,
                from_precond=from_precond,
                to_precond=to_precond,
                not_through=not_through,
                keep_driving_logic=True,
                exclude_control_logic=False
            )

            out_f.write(spv_check)
            out_f.write("\n")
        
        # Read template content
        with open(template, "r") as f:
            template_content = f.read()

        # Append template content
        out_f.write(template_content)

if __name__ == "__main__":
    generate_header()
    generate_spv_tcl()
