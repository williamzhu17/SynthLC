from util import *

def generate_spv_checks():
    """
    Generates the SPV checks
    """

    print("generating SPV checks")

def prune_header_sv():
    """
    Prune the header.sv file to only include PL annotations of reachable ones
    """

    header_sv = "./header.sv"
    reachable_pls = get_array("./xCoverAPerflocDiv/cover_individual.txt")
    pruned_header_sv = "./xSquashDetect/reachable_pls_header.sv"

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
    

def generate_file_header():
    """
    Generate the file header by concatenating the topsim, macro, and properties
    TODO remove Check cover_individual_update_file_.sh for how to create
    """

    topsim = "./src/topsim.sv"
    macro = "./src/macro.sv"
    cover = "./synthlc/i_DIV_out/xCoverAPerflocDiv/out/cover_individual.sv"
    out = "./synthlc/i_DIV_out/xCoverAPerflocDiv/cover_individual_top.sv"

    # Read topsim once
    with open(topsim, "r") as f:
        topsim_lines = f.readlines()

    with open(out, "w") as out_f:
        # Write entire topsim except the last line
        out_f.writelines(topsim_lines[:-1])

        # Write macro
        with open(macro, "r") as f:
            out_f.write(f.read())

        # Write cover
        with open(cover, "r") as f:
            out_f.write(f.read())

        # Write empty line
        out_f.write("\n")

        # Write last line of topsim
        out_f.write(topsim_lines[-1])

if __name__ == "__main__":
    # Generate SPV Checks
    generate_spv_checks()

    # Prune header.sv
    prune_header_sv()

    # Generate File Header
    print("generating file header")

    # Prepare file list
    print("generating file list")