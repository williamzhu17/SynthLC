import os
import re
import sys
sys.path.append("../../src")
from util import *

def generate_header(i1_opcode):
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
        directory = "../../opcodes_gen_all"

        # Get list of all files in the opcodes directory
        files = os.listdir(directory)
        matched_file = None
        for file in files:
            if file == f"{i1_opcode}.sv":
                matched_file = os.path.join(directory, file)
                break
        if not matched_file:
            raise ValueError(f"{i1_opcode}.sv not found in {directory}")

        # Read the entire matched opcode file into a single string
        with open(matched_file, "r") as f:
            file_contents = f.read()

        out_f.write(file_contents.replace("i0", "i1"))

        out_f.write("\n")

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

def generate_spv_tcl():
    """
    Generate the SPV TCL file
    """

    template = "./squash_detect_template.tcl"
    instruction_signal_prefix = "id_stage_i.instruction"
    out = "./squash_detect.tcl"
    
    with open(out, "w") as out_f:
        # Write SPV checks
        from_signal = "id_stage_i.instruction[24:15] id_stage_i.instruction[11:7]"
        from_precond = "i1_instn_begin"
        # to_signal = "in_perf_locs"
        to_signal = "left_perf_locs"
        # to_signal = "flush_ctrl_if flush_ctrl_id flush_ctrl_ex flush_unissued_instr_ctrl_id"
        # to_precond = "i0_issued_before || instn_begin"
        # to_precond = "in_perf_locs && $past(in_perf_locs) && i0_issued_before"
        # to_precond = "!in_perf_locs && $past(in_perf_locs) && !seen_instn_committed && !instn_committed"
        # to_precond = "$past(in_perf_locs) && !seen_instn_committed && !instn_committed && i0_issued_before"
        # to_precond = "$past(in_perf_locs) && !seen_instn_committed && !instn_committed"
        to_precond = "!left_perf_locs"
        # to_precond = None

        # not_through = "issue_stage_i.i_issue_read_operands.forward_rs1 issue_stage_i.i_issue_read_operands.forward_rs2 issue_stage_i.i_issue_read_operands.forward_rs3"
        # not_through = "issue_stage_i.i_issue_read_operands.*"
        # not_through = "issue_stage_i.rs1_iro_sb issue_stage_i.rs2_iro_sb issue_stage_i.rs3_iro_sb"
        # not_through += " issue_stage_i.i_issue_read_operands.i_ariane_regfile.*"
        # not_through += " issue_stage_i.i_issue_read_operands.forward_rs1 issue_stage_i.i_issue_read_operands.forward_rs2 issue_stage_i.i_issue_read_operands.forward_rs3"
        # not_through = "issue_stage_i.i_issue_read_operands.stall issue_stage_i.i_issue_read_operands.issue_ack_o"
        # not_through = "ex_stage_i.branch_unit_i.resolved_branch_o.is_mispredict"
        # not_through = "issue_stage_i.i_scoreboard.rs1_fwd_req issue_stage_i.i_scoreboard.rs2_fwd_req issue_stage_i.i_scoreboard.rs3_fwd_req"
        # not_through = "issue_stage_i.i_issue_read_operands.forward_rs1 issue_stage_i.i_issue_read_operands.forward_rs2 issue_stage_i.i_issue_read_operands.forward_rs3"
        # not_through = "issue_stage_i.i_issue_read_operands.rd_clobber_gpr_i issue_stage_i.i_issue_read_operands.rd_clobber_fpr_i"
        # not_through = None
        
        not_through = "issue_stage_i.i_issue_read_operands.rs1_i issue_stage_i.i_issue_read_operands.rs1_valid_i issue_stage_i.i_issue_read_operands.forward_rs1 issue_stage_i.i_issue_read_operands.rs2_i issue_stage_i.i_issue_read_operands.rs2_valid_i issue_stage_i.i_issue_read_operands.forward_rs2 issue_stage_i.i_issue_read_operands.rs3_i issue_stage_i.i_issue_read_operands.rs3_valid_i issue_stage_i.i_issue_read_operands.forward_rs3 issue_stage_i.i_issue_read_operands.rd_clobber_gpr_i issue_stage_i.i_issue_read_operands.rd_clobber_fpr_i issue_stage_i.i_issue_read_operands.i_ariane_regfile.waddr_i issue_stage_i.i_issue_read_operands.i_ariane_regfile.wdata_i issue_stage_i.i_issue_read_operands.i_ariane_regfile.we_i"

        spv_check = generate_spv_check(
            name=f"BNE_SQUASHER",
            from_signal=from_signal,
            to_signal=to_signal,
            from_precond=from_precond,
            to_precond=to_precond,
            keep_driving_logic=True, # TODO check if we need
            exclude_control_logic=False,
            not_through=not_through
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
    generate_header("BNE")
    generate_spv_tcl()
