import os
import re
import sys
sys.path.append("../../src")
from util import *

def i1_signal_detect_string(opcode, opcode_requirement_list):
    """
    Generates signals for header. For example:
    wire i1_NOP = read_instr == 32'h00000013 && i1_instn_fetched;
    """

    replaced_requirements = " && ".join([req.replace("i0", "read_instr") for req in opcode_requirement_list])

    signal_string = f"wire i1_{opcode} = {replaced_requirements} && i1_instn_fetched;"
    seen_string = f"reg seen_i1_{opcode};"

    return f"{signal_string}\n{seen_string}\n"

def always_block_gen(opcode_list):
    """
    Generates the always block for the seen signals
    """

    always_block = "always @(posedge clk_i) begin\n"
    always_block += "  if (!rst_ni) begin\n"

    for opcode in opcode_list:
        always_block += f"    seen_i1_{opcode} <= 1'b0;\n"

    always_block += "  end else begin\n"

    for opcode in opcode_list:
        always_block += f"    seen_i1_{opcode} <= i1_{opcode} ? 1'b1 : seen_i1_{opcode};\n"

    always_block += "  end\n"
    always_block += "end\n"

    return always_block

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

        opcodes = obtain_opcodes()

        # Write the other opcode signals
        for opcode, opcode_portions in opcodes.items():
            signal_detect_string = i1_signal_detect_string(opcode, opcode_portions)
            out_f.write(signal_detect_string)

        out_f.write("\n")

        # Write always block for seen signals
        out_f.write(always_block_gen(opcodes.keys()))

        out_f.write("\n")

        # Write left_perf_locs wires
        for opcode in opcodes.keys():
            no_i1_more_than_once = "!i1_fetched_more_than_once && !(i1_instn_fetched && seen_i1_fetched)"

            left_perf_locs_string = f"wire left_perf_locs_{opcode} = !in_perf_locs && prev_in_perf_locs ? i0_fetched_before && seen_i1_{opcode} && !seen_i1_committed && !i1_committed && {no_i1_more_than_once} : 1'b0;\n"
            out_f.write(left_perf_locs_string)

            # TODO: need to figure out how to handle JALR
            no_jump_to_trap = "!i1_branch_to_trap && !i1_jal_to_trap"

            icache_req_trap = f"tmp_icache_dreq_if_cache.vaddr == trap_vector_base_commit_pcgen && tmp_icache_dreq_if_cache.req"
            left_perf_locs_exception_string = f"wire left_perf_locs_exception_{opcode} = !in_perf_locs && prev_in_perf_locs && {icache_req_trap} ? i0_fetched_before && seen_i1_{opcode} && !seen_i1_committed && !i1_committed && {no_jump_to_trap} && {no_i1_more_than_once} : 1'b0;\n"
            out_f.write(left_perf_locs_exception_string)

            no_icache_req_trap = f"tmp_icache_dreq_if_cache.vaddr != trap_vector_base_commit_pcgen && tmp_icache_dreq_if_cache.req"
            left_perf_locs_speculation_string = f"wire left_perf_locs_speculation_{opcode} = !in_perf_locs && prev_in_perf_locs && {no_icache_req_trap} ? i0_fetched_before && seen_i1_{opcode} && !seen_i1_committed && !i1_committed && {no_jump_to_trap} && {no_i1_more_than_once} : 1'b0;\n"
            out_f.write(left_perf_locs_speculation_string)
        
        out_f.write("\n")

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
    out = "./squash_detect.tcl"

    opcodes = obtain_opcodes()

    with open(out, "w") as out_f:
        for opcode, opcode_portions in opcodes.items():
            # if opcode != "BEQ" and opcode != "BGEU" and opcode != "BGE" and opcode != "BLTU" and opcode != "BLT" and opcode != "BNE" and opcode != "CSRRCI" and opcode != "CSRRC" and opcode != "CSRRSI" and opcode != "CSRRS" and opcode != "CSRRWI" and opcode != "CSRRW" and opcode != "EBREAK" and opcode != "ECALL" and opcode != "JALR":
            #     continue

            # if opcode != "BEQ" and opcode != "CSRRCI" and opcode != "EBREAK" and opcode != "AND" and opcode != "JAL" and opcode != "JALR":
            #     continue

            if opcode == "NOP":
                continue

            from_signal = "read_instr"
            from_precond = f"i1_NOP"

            to_signal = f"left_perf_locs_{opcode}"
            to_signal_exception = f"left_perf_locs_exception_{opcode}"
            to_signal_speculation = f"left_perf_locs_speculation_{opcode}"
            to_precond = f"!left_perf_locs_{opcode} && in_perf_locs && $past(in_perf_locs) && i0_fetched_before"

            # Not through these signals
            not_through = "issue_stage_i.i_issue_read_operands.rs1_i issue_stage_i.i_issue_read_operands.rs1_valid_i issue_stage_i.i_issue_read_operands.forward_rs1 issue_stage_i.i_issue_read_operands.rs2_i issue_stage_i.i_issue_read_operands.rs2_valid_i issue_stage_i.i_issue_read_operands.forward_rs2 issue_stage_i.i_issue_read_operands.rs3_i issue_stage_i.i_issue_read_operands.rs3_valid_i issue_stage_i.i_issue_read_operands.forward_rs3 issue_stage_i.i_issue_read_operands.rd_clobber_gpr_i issue_stage_i.i_issue_read_operands.rd_clobber_fpr_i issue_stage_i.i_issue_read_operands.i_ariane_regfile.waddr_i issue_stage_i.i_issue_read_operands.i_ariane_regfile.wdata_i issue_stage_i.i_issue_read_operands.i_ariane_regfile.we_i"

            not_through += " issue_stage_i.i_issue_read_operands.we_fpr_i issue_stage_i.i_issue_read_operands.we_gpr_i"
            not_through += " issue_stage_i.i_issue_read_operands.waddr_i"
            not_through += " issue_stage_i.i_issue_read_operands.issue_instr_i.rd"  # Don't care about destination, as we only care if previous state can induce behaviors

            # TODO not sure about these
            not_through += " issue_stage_i.i_issue_read_operands.stall"
            not_through += " no_st_pending_commit"

            # not_through += " tmp_icache_dreq_if_cache"

            # Exception case
            # Need to account for timing behaviors and how it fetch addr == trap addr can be potentially delayed
            spv_check_exception = generate_spv_check(
                name=f"{opcode}_EXCEPTION",
                from_signal=from_signal,
                to_signal=to_signal_exception,
                from_precond=from_precond,
                to_precond=to_precond,
                not_through=not_through,
                keep_driving_logic=True,
                exclude_control_logic=False
            )

            # out_f.write(spv_check_exception)
            # out_f.write("\n")

            # Speculation case
            spv_check_speculation = generate_spv_check(
                name=f"{opcode}_SPECULATION",
                from_signal=from_signal,
                to_signal=to_signal_speculation,
                from_precond=from_precond,
                to_precond=to_precond,
                not_through=not_through,
                keep_driving_logic=True,
                exclude_control_logic=False
            )

            # out_f.write(spv_check_speculation)
            # out_f.write("\n")

            # General case
            spv_check = generate_spv_check(
                name=f"{opcode}_GENERAL",
                from_signal=from_signal,
                to_signal=to_signal,
                from_precond=from_precond,
                to_precond=to_precond,
                not_through=not_through,
                keep_driving_logic=True,
                exclude_control_logic=False
            )

            # TODO: uncomment this
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
