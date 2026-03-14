// Set up common formal environment for CVA6 with symbolic instruction being
// driven at IF stage and assumptions that constrain the inputs from frontend,
// which is bbox for verificaiton purpose

// Post-trace: any instruction encoding but invalid
// Assume IUV issued at first cycle after reset
// Symbolic reset on the memory and regfile
`define INTRA_TRANSMITTER 

// =============================================================================
// Processor setup
// =============================================================================

IN_OP_MODE: assume property (@(posedge clk_i) rst_ni == 1'd1);
NOHALT: assume property (@(posedge clk_i) commit_stage_i.halt_i == 1'b0);
NO_COMPRESSED_INSTNS: assume property (@(posedge clk_i) read_instr[1:0] == 2'b11);
ALIGNED_PC: assume property (@(posedge clk_i) tmp_icache_dreq_if_cache.vaddr[1:0] == 2'b00);

READ_INSTR_CHANGE_VALID: assume property (@(posedge clk_i)
    (tmp_icache_dreq_cache_if.valid && !$past(tmp_icache_dreq_cache_if.valid)) |-> 
	(read_instr == $past(read_instr))
);

// reg prev_read_instr_valid;
// reg prev_read_instr;
// reg seen_read_instr_change_invalid;

// wire read_instr_change_invalid = 
//     !prev_read_instr_valid && tmp_icache_dreq_cache_if.valid &&
// 	(read_instr != prev_read_instr);

// always @(posedge clk_i) begin
// 	if (!rst_ni) begin
// 		prev_read_instr_valid <= 1'b0;
// 		prev_read_instr <= '0;
// 		seen_read_instr_change_invalid <= 1'b0;
// 	end else begin
//         prev_read_instr_valid <= tmp_icache_dreq_cache_if.valid;
// 		prev_read_instr <= read_instr;
// 		seen_read_instr_change_invalid <= read_instr_change_invalid ? 1'b1 : seen_read_instr_change_invalid;
// 	end
// end

// =============================================================================
// icache-legal-setup
// =============================================================================

// TODO check if we need

// =============================================================================
// Frontend-legal-setup (since we bbox) and processor in operation
// =============================================================================

//BBOX_AMO_REQ: assume property (@(posedge clk_i) 
//      commit_stage_i.amo_resp_i.ack == 1'b0);
//BRANCH: assume property (@(posedge clk_i) 
//      id_stage_i.fetch_entry_i.branch_predict.predict_address != pc0);

// NON_EXCEPTION_FRONTEND: assume property (@(posedge clk_i)
//   i_frontend.fetch_entry_o.ex.valid == 1'b0
//   // tag this fetched instruction is not exceptioned already at front-end
//   // (e.g., INSTR_PAGE_FAULT or INSTR_ACCESS_FAULT)
// );
// IF_ID_CONTRACT: assume property (@(posedge clk_i)
//   // yet ack then hold
//   (id_stage_i.fetch_entry_valid_i && !(fetch_ready_id_if)) |=>
//   (
//   ($past(id_stage_i.fetch_entry_valid_i) == id_stage_i.fetch_entry_valid_i) &&
//   ($past(id_stage_i.instruction) == id_stage_i.instruction) &&
//   ($past(id_stage_i.fetch_entry_i.address) == id_stage_i.fetch_entry_i.address)
//   )
// );

// Assume that previous fetched PC will be different from current fetched PC
// wire fetch_fire = id_stage_i.fetch_entry_valid_i && fetch_ready_id_if;
// wire [63:0] fetch_pc = id_stage_i.fetch_entry_i.address;

// reg have_last_fire;
// reg [63:0] last_fire_pc;

// always_ff @(posedge clk_i) begin
//   if (!rst_ni) begin
//     have_last_fire <= 1'b0;
//     last_fire_pc <= '0;
//   end else if (fetch_fire) begin
//     have_last_fire <= 1'b1;
//     last_fire_pc <= fetch_pc;
//   end
// end

// PC_DIFF_LAST_INSTN: assume property (@(posedge clk_i) disable iff (!rst_ni)
//   fetch_fire && have_last_fire
//   |-> fetch_pc != last_fire_pc
// );

// PC_ALIGNED: assume property (@(posedge clk_i) id_stage_i.fetch_entry_i.address[1:0] == 2'b00);

// =============================================================================
// Set up instruction of interest 
// i0 is for the instruction that we are detecting will be squashed
// =============================================================================
wire [32-1:0] i0;
i0_const: assume property (@(posedge clk_i) CONST(i0));

// =============================================================================
// Set up pc value, instruction issue, and execution contexts
// =============================================================================
// (pc0, i0)
wire [64-1:0] pc0;

pc0_const: assume property (@(posedge clk_i) CONST(pc0));
pc0_nozero: assume property (@(posedge clk_i) pc0 != '0);

wire instn_fetched = (tmp_icache_dreq_cache_if.valid &&
	                  tmp_icache_dreq_cache_if.vaddr == pc0);
// wire instn_begin = (id_stage_i.fetch_entry_valid_i && 
//                     id_stage_i.fetch_entry_i.address == pc0);

pc0_i0_assoc_1: assume property (@(posedge clk_i)
    tmp_icache_dreq_cache_if.vaddr == pc0 |-> read_instr == i0);
pc0_i0_assoc_2: assume property (@(posedge clk_i) 
    tmp_icache_dreq_cache_if.vaddr == pc0 |-> tmp_icache_dreq_cache_if.valid == 1'b1);

FETCH_ONCE: assume property (@(posedge clk_i) instn_fetched |=>
    always !(tmp_icache_dreq_cache_if.vaddr == pc0)
);
EVENTUAL_FETCH: assume property (@(posedge clk_i) first |->
    s_eventually(instn_fetched));


// ISSUE_ONCE: assume property (@(posedge clk_i) instn_begin |=> 
//         always !(id_stage_i.fetch_entry_i.address == pc0));
// EVENTUAL_ISSUE: assume property (@(posedge clk_i) first |->
//     s_eventually(instn_begin));
// EXE_IUV: assume property (@(posedge clk_i) instn_begin |-> fetch_ready_id_if);

EVENTUAL_IN_PERF_LOCS: assume property (@(posedge clk_i) instn_fetched |-> s_eventually(in_perf_locs));

// Instruction is being committed
wire instn_committed = 
    (commit_stage_i.commit_instr_i[0].pc == pc0 && commit_stage_i.commit_ack_o[0]) || 
    (commit_stage_i.commit_instr_i[1].pc == pc0 && commit_stage_i.commit_ack_o[1]);

reg seen_instn_committed;

always @(posedge clk_i) begin
    if (!rst_ni) begin
        seen_instn_committed <= 1'b0;
    end else if (instn_committed) begin
        seen_instn_committed <= 1'b1;
		end else begin
			  seen_instn_committed <= seen_instn_committed;
		end
end

// =============================================================================
// Set up instruction of interest 
// i1 is for the instruction that we are testing will cause squash
// =============================================================================
wire [32-1:0] i1;
i1_const: assume property (@(posedge clk_i) CONST(i1));
i1_nop: assume property (@(posedge clk_i) i1 == 32'h00000013);

// =============================================================================
// Set up pc value, instruction issue, and execution contexts
// =============================================================================
// (pc1, i1)
wire [64-1:0] pc1;

pc1_const: assume property (@(posedge clk_i) CONST(pc1));
pc1_nozero: assume property (@(posedge clk_i) pc1 != '0);
DIFF_PC: assume property (@(posedge clk_i) pc1 != pc0);

wire i1_instn_fetched = (tmp_icache_dreq_cache_if.valid &&
	                  tmp_icache_dreq_cache_if.vaddr == pc1);
wire i1_instn_begin = (id_stage_i.fetch_entry_valid_i && 
                       id_stage_i.fetch_entry_i.address == pc1 &&
					   id_stage_i.fetch_entry_i.instruction == i1);

pc1_i1_assoc_1: assume property (@(posedge clk_i) 
    tmp_icache_dreq_cache_if.vaddr == pc1 |-> read_instr == i1);
pc1_i1_assoc_2: assume property (@(posedge clk_i) 
    tmp_icache_dreq_cache_if.vaddr == pc1 |-> tmp_icache_dreq_cache_if.valid == 1'b1);

FETCH_ONCE_I1: assume property (@(posedge clk_i) i1_instn_fetched |=>
    always !(tmp_icache_dreq_cache_if.vaddr == pc1)
);
EVENTUAL_FETCH_I1: assume property (@(posedge clk_i) first |->
    s_eventually(i1_instn_fetched));

// ISSUE_ONCE_I1: assume property (@(posedge clk_i) i1_instn_begin |=> 
//         always !(id_stage_i.fetch_entry_i.address == pc1));
// EVENTUAL_ISSUE_I1: assume property (@(posedge clk_i) first |->
//     s_eventually(i1_instn_begin));
// EXE_IUV_I1: assume property (@(posedge clk_i) i1_instn_begin |-> fetch_ready_id_if);

reg seen_i1_fetched;
reg i1_fetched_more_than_once;

always @(posedge clk_i) begin
	if (!rst_ni) begin
		seen_i1_fetched <= 1'b0;
		i1_fetched_more_than_once <= 1'b0;
	end else begin
		seen_i1_fetched <= i1_instn_fetched ? 1'b1 : seen_i1_fetched;
		i1_fetched_more_than_once <= i1_instn_fetched && seen_i1_fetched ? 1'b1 : i1_fetched_more_than_once;
	end
end

// i1 is being committed
wire i1_committed = 
    (commit_stage_i.commit_instr_i[0].pc == pc1 && commit_stage_i.commit_ack_o[0]) || 
    (commit_stage_i.commit_instr_i[1].pc == pc1 && commit_stage_i.commit_ack_o[1]);

reg seen_i1_committed;

always @(posedge clk_i) begin
	if (!rst_ni) begin
		seen_i1_committed <= 1'b0;
	end else begin
        seen_i1_committed <= i1_committed ? 1'b1 : seen_i1_committed;
	end
end

// =============================================================================
// Set up relations between i0 and i1
// =============================================================================

// reg i0_issued_before;
// always @(posedge clk_i) begin
//     if (!rst_ni) begin
//         i0_issued_before <= 1'b0;
//     end else if (instn_begin) begin
//         i0_issued_before <= 1'b1;
//     end
// end

reg i0_fetched_before;
always @(posedge clk_i) begin
    if (!rst_ni) begin
        i0_fetched_before <= 1'b0;
    end else if (instn_fetched) begin
        i0_fetched_before <= 1'b1;
    end
end

// reg i1_issued_before;
// always @(posedge clk_i) begin
//     if (!rst_ni) begin
//         i1_issued_before <= 1'b0;
//     end else if (i1_instn_begin) begin
//         i1_issued_before <= 1'b1;
//     end
// end

reg i1_fetched_before;
always @(posedge clk_i) begin
    if (!rst_ni) begin
        i1_fetched_before <= 1'b0;
    end else if (i1_instn_fetched) begin
        i1_fetched_before <= 1'b1;
    end
end

// I1_ISSUE_HB_I0: assume property (@(posedge clk_i) instn_begin |-> i1_issued_before);
// I0_EVENTUAL_ISSUE_AFTER_I1: assume property (@(posedge clk_i) i1_instn_begin |-> s_eventually(instn_begin));
I1_FETCH_HB_I0: assume property (@(posedge clk_i) instn_fetched |-> i1_fetched_before);
I0_EVENTUAL_FETCH_AFTER_I1: assume property (@(posedge clk_i) i1_instn_fetched |-> s_eventually(instn_fetched));

// N instructions between i1 and i0
reg [7:0] instn_count_after_i1;
reg counting;

always @(posedge clk_i) begin
	if (!rst_ni) begin
		instn_count_after_i1 <= '0;
		counting <= 1'b0;
	end else if (i1_instn_fetched) begin
		instn_count_after_i1 <= '0;
		counting <= 1'b1;
	end else if (counting && tmp_icache_dreq_cache_if.valid) begin
		instn_count_after_i1 <= instn_count_after_i1 + 1;
		counting <= counting;
	end else begin
        instn_count_after_i1 <= instn_count_after_i1;
        counting <= counting;
	end
end

// Step 4: Uncomment this and adjust N
// I1_N_INSTNS_BEFORE_I0: assume property (@(posedge clk_i) instn_fetched |-> instn_count_after_i1 == 0);
// Step 4: END

// =============================================================================
// ## No jump to trap
// ============================================================================= 

// Branch instructions
wire is_i1_branch = read_instr[6:0] == 7'b1100011 && i1_instn_fetched;
wire [12:0] branch_offset = {
	read_instr[31],
	read_instr[7],
	read_instr[30:25],
	read_instr[11:8],
	1'b0
};
wire signed [64-1:0] branch_offset_signed = {{51{branch_offset[12]}}, branch_offset};
wire [64-1:0] branch_target = tmp_icache_dreq_cache_if.vaddr + branch_offset_signed;

reg [64-1:0] i1_branch_target_reg;
reg i1_branch_target_valid;

always @(posedge clk_i) begin
	if (!rst_ni) begin
		i1_branch_target_reg <= 1'b0;
		i1_branch_target_valid <= 1'b0;
	end else begin
		i1_branch_target_reg <= is_i1_branch ? branch_target : i1_branch_target_reg;
		i1_branch_target_valid <= is_i1_branch ? 1'b1 : i1_branch_target_valid;
	end
end

wire i1_branch_to_trap = (i1_branch_target_reg == trap_vector_base_commit_pcgen) && i1_branch_target_valid;

// JAL instruction
wire is_i1_jal = read_instr[6:0] == 7'b1101111 && i1_instn_fetched;
wire [12:0] jal_offset = read_instr[31:20];
wire signed [64-1:0] jal_offset_signed = {{51{jal_offset[12]}}, jal_offset};
wire [64-1:0] jal_target = tmp_icache_dreq_cache_if.vaddr + jal_offset_signed;

reg [64-1:0] i1_jal_target_reg;
reg i1_jal_target_valid;

always @(posedge clk_i) begin
	if (!rst_ni) begin
		i1_jal_target_reg <= 1'b0;
		i1_jal_target_valid <= 1'b0;
	end else begin
		i1_jal_target_reg <= is_i1_jal ? jal_target : i1_jal_target_reg;
		i1_jal_target_valid <= is_i1_jal ? 1'b1 : i1_jal_target_valid;
	end
end

wire i1_jal_to_trap = (i1_jal_target_reg == trap_vector_base_commit_pcgen) && i1_jal_target_valid;

// JALR instruction
// TODO: Need a way to handle this

// =============================================================================
// ## Performing location annotation
// ============================================================================= 


wire serdiv_unit_divide_s1 = 
	(ex_stage_i.i_mult.i_div.pc_q == pc0) && 
	(ex_stage_i.i_mult.i_div.state_q == 2'd1) && 
	 1'b1; 
wire serdiv_unit_divide_s2 = 
	(ex_stage_i.i_mult.i_div.pc_q == pc0) && 
	(ex_stage_i.i_mult.i_div.state_q == 2'd2) && 
	 1'b1; 
wire id_stage_s1 = 
	(id_stage_i.issue_q.sbe.pc == pc0) && 
	(id_stage_i.issue_q.valid == 1'd1) && 
	 1'b1; 
wire issue_s1 = 
	(issue_stage_i.i_issue_read_operands.pc_o == pc0) && 
	(issue_stage_i.i_issue_read_operands.alu_valid_q == 1'd0) && 
	(issue_stage_i.i_issue_read_operands.lsu_valid_q == 1'd0) && 
	(issue_stage_i.i_issue_read_operands.mult_valid_q == 1'd0) && 
	(issue_stage_i.i_issue_read_operands.fpu_valid_q == 1'd0) && 
	(issue_stage_i.i_issue_read_operands.csr_valid_q == 1'd0) && 
	(issue_stage_i.i_issue_read_operands.branch_valid_q == 1'd1) && 
	 1'b1; 
wire issue_s2 = 
	(issue_stage_i.i_issue_read_operands.pc_o == pc0) && 
	(issue_stage_i.i_issue_read_operands.alu_valid_q == 1'd0) && 
	(issue_stage_i.i_issue_read_operands.lsu_valid_q == 1'd0) && 
	(issue_stage_i.i_issue_read_operands.mult_valid_q == 1'd0) && 
	(issue_stage_i.i_issue_read_operands.fpu_valid_q == 1'd0) && 
	(issue_stage_i.i_issue_read_operands.csr_valid_q == 1'd1) && 
	(issue_stage_i.i_issue_read_operands.branch_valid_q == 1'd0) && 
	 1'b1; 
wire issue_s8 = 
	(issue_stage_i.i_issue_read_operands.pc_o == pc0) && 
	(issue_stage_i.i_issue_read_operands.alu_valid_q == 1'd0) && 
	(issue_stage_i.i_issue_read_operands.lsu_valid_q == 1'd0) && 
	(issue_stage_i.i_issue_read_operands.mult_valid_q == 1'd1) && 
	(issue_stage_i.i_issue_read_operands.fpu_valid_q == 1'd0) && 
	(issue_stage_i.i_issue_read_operands.csr_valid_q == 1'd0) && 
	(issue_stage_i.i_issue_read_operands.branch_valid_q == 1'd0) && 
	 1'b1; 
wire issue_s16 = 
	(issue_stage_i.i_issue_read_operands.pc_o == pc0) && 
	(issue_stage_i.i_issue_read_operands.alu_valid_q == 1'd0) && 
	(issue_stage_i.i_issue_read_operands.lsu_valid_q == 1'd1) && 
	(issue_stage_i.i_issue_read_operands.mult_valid_q == 1'd0) && 
	(issue_stage_i.i_issue_read_operands.fpu_valid_q == 1'd0) && 
	(issue_stage_i.i_issue_read_operands.csr_valid_q == 1'd0) && 
	(issue_stage_i.i_issue_read_operands.branch_valid_q == 1'd0) && 
	 1'b1; 
wire issue_s32 = 
	(issue_stage_i.i_issue_read_operands.pc_o == pc0) && 
	(issue_stage_i.i_issue_read_operands.alu_valid_q == 1'd1) && 
	(issue_stage_i.i_issue_read_operands.lsu_valid_q == 1'd0) && 
	(issue_stage_i.i_issue_read_operands.mult_valid_q == 1'd0) && 
	(issue_stage_i.i_issue_read_operands.fpu_valid_q == 1'd0) && 
	(issue_stage_i.i_issue_read_operands.csr_valid_q == 1'd0) && 
	(issue_stage_i.i_issue_read_operands.branch_valid_q == 1'd0) && 
	 1'b1; 
wire lsq_enq_0_s1 = 
	(ex_stage_i.lsu_i.lsu_bypass_i.mem_q[0].pc == pc0) && 
	(ex_stage_i.lsu_i.lsu_bypass_i.mem_q[0].valid == 1'd1) && 
	 1'b1; 
wire lsq_enq_1_s1 = 
	(ex_stage_i.lsu_i.lsu_bypass_i.mem_q[1].pc == pc0) && 
	(ex_stage_i.lsu_i.lsu_bypass_i.mem_q[1].valid == 1'd1) && 
	 1'b1; 
wire scb_0_s12 = 
	(issue_stage_i.i_scoreboard.mem_q[0].sbe.pc == pc0) && 
	(issue_stage_i.i_scoreboard.mem_q[0].issued == 1'd1) && 
	(issue_stage_i.i_scoreboard.mem_q[0].sbe.valid == 1'd1) && 
	(issue_stage_i.i_scoreboard.mem_q[0].sbe.ex.valid == 1'd0) && 
	(((issue_stage_i.i_scoreboard.mem_n[0].issued == 1'b0) && ((issue_stage_i.i_scoreboard.commit_ack_i[1] == 1'b1 && issue_stage_i.i_scoreboard.commit_pointer_q[1] == 2'd0) || (issue_stage_i.i_scoreboard.commit_ack_i[0] == 1'b1 && issue_stage_i.i_scoreboard.commit_pointer_q[0] == 2'd0)))  == 1'd0) && 
	 1'b1; 
wire scb_0_s13 = 
	(issue_stage_i.i_scoreboard.mem_q[0].sbe.pc == pc0) && 
	(issue_stage_i.i_scoreboard.mem_q[0].issued == 1'd1) && 
	(issue_stage_i.i_scoreboard.mem_q[0].sbe.valid == 1'd1) && 
	(issue_stage_i.i_scoreboard.mem_q[0].sbe.ex.valid == 1'd0) && 
	(((issue_stage_i.i_scoreboard.mem_n[0].issued == 1'b0) && ((issue_stage_i.i_scoreboard.commit_ack_i[1] == 1'b1 && issue_stage_i.i_scoreboard.commit_pointer_q[1] == 2'd0) || (issue_stage_i.i_scoreboard.commit_ack_i[0] == 1'b1 && issue_stage_i.i_scoreboard.commit_pointer_q[0] == 2'd0)))  == 1'd1) && 
	 1'b1; 
wire scb_0_s14 = 
	(issue_stage_i.i_scoreboard.mem_q[0].sbe.pc == pc0) && 
	(issue_stage_i.i_scoreboard.mem_q[0].issued == 1'd1) && 
	(issue_stage_i.i_scoreboard.mem_q[0].sbe.valid == 1'd1) && 
	(issue_stage_i.i_scoreboard.mem_q[0].sbe.ex.valid == 1'd1) && 
	(((issue_stage_i.i_scoreboard.mem_n[0].issued == 1'b0) && ((issue_stage_i.i_scoreboard.commit_ack_i[1] == 1'b1 && issue_stage_i.i_scoreboard.commit_pointer_q[1] == 2'd0) || (issue_stage_i.i_scoreboard.commit_ack_i[0] == 1'b1 && issue_stage_i.i_scoreboard.commit_pointer_q[0] == 2'd0)))  == 1'd0) && 
	 1'b1; 
wire scb_0_s8 = 
	(issue_stage_i.i_scoreboard.mem_q[0].sbe.pc == pc0) && 
	(issue_stage_i.i_scoreboard.mem_q[0].issued == 1'd1) && 
	(issue_stage_i.i_scoreboard.mem_q[0].sbe.valid == 1'd0) && 
	(issue_stage_i.i_scoreboard.mem_q[0].sbe.ex.valid == 1'd0) && 
	(((issue_stage_i.i_scoreboard.mem_n[0].issued == 1'b0) && ((issue_stage_i.i_scoreboard.commit_ack_i[1] == 1'b1 && issue_stage_i.i_scoreboard.commit_pointer_q[1] == 2'd0) || (issue_stage_i.i_scoreboard.commit_ack_i[0] == 1'b1 && issue_stage_i.i_scoreboard.commit_pointer_q[0] == 2'd0)))  == 1'd0) && 
	 1'b1; 
wire scb_1_s12 = 
	(issue_stage_i.i_scoreboard.mem_q[1].sbe.pc == pc0) && 
	(issue_stage_i.i_scoreboard.mem_q[1].issued == 1'd1) && 
	(issue_stage_i.i_scoreboard.mem_q[1].sbe.valid == 1'd1) && 
	(issue_stage_i.i_scoreboard.mem_q[1].sbe.ex.valid == 1'd0) && 
	(((issue_stage_i.i_scoreboard.mem_n[1].issued == 1'b0) && ((issue_stage_i.i_scoreboard.commit_ack_i[1] == 1'b1 && issue_stage_i.i_scoreboard.commit_pointer_q[1] == 2'd1) || (issue_stage_i.i_scoreboard.commit_ack_i[0] == 1'b1 && issue_stage_i.i_scoreboard.commit_pointer_q[0] == 2'd1)))  == 1'd0) && 
	 1'b1; 
wire scb_1_s13 = 
	(issue_stage_i.i_scoreboard.mem_q[1].sbe.pc == pc0) && 
	(issue_stage_i.i_scoreboard.mem_q[1].issued == 1'd1) && 
	(issue_stage_i.i_scoreboard.mem_q[1].sbe.valid == 1'd1) && 
	(issue_stage_i.i_scoreboard.mem_q[1].sbe.ex.valid == 1'd0) && 
	(((issue_stage_i.i_scoreboard.mem_n[1].issued == 1'b0) && ((issue_stage_i.i_scoreboard.commit_ack_i[1] == 1'b1 && issue_stage_i.i_scoreboard.commit_pointer_q[1] == 2'd1) || (issue_stage_i.i_scoreboard.commit_ack_i[0] == 1'b1 && issue_stage_i.i_scoreboard.commit_pointer_q[0] == 2'd1)))  == 1'd1) && 
	 1'b1; 
wire scb_1_s14 = 
	(issue_stage_i.i_scoreboard.mem_q[1].sbe.pc == pc0) && 
	(issue_stage_i.i_scoreboard.mem_q[1].issued == 1'd1) && 
	(issue_stage_i.i_scoreboard.mem_q[1].sbe.valid == 1'd1) && 
	(issue_stage_i.i_scoreboard.mem_q[1].sbe.ex.valid == 1'd1) && 
	(((issue_stage_i.i_scoreboard.mem_n[1].issued == 1'b0) && ((issue_stage_i.i_scoreboard.commit_ack_i[1] == 1'b1 && issue_stage_i.i_scoreboard.commit_pointer_q[1] == 2'd1) || (issue_stage_i.i_scoreboard.commit_ack_i[0] == 1'b1 && issue_stage_i.i_scoreboard.commit_pointer_q[0] == 2'd1)))  == 1'd0) && 
	 1'b1; 
wire scb_1_s8 = 
	(issue_stage_i.i_scoreboard.mem_q[1].sbe.pc == pc0) && 
	(issue_stage_i.i_scoreboard.mem_q[1].issued == 1'd1) && 
	(issue_stage_i.i_scoreboard.mem_q[1].sbe.valid == 1'd0) && 
	(issue_stage_i.i_scoreboard.mem_q[1].sbe.ex.valid == 1'd0) && 
	(((issue_stage_i.i_scoreboard.mem_n[1].issued == 1'b0) && ((issue_stage_i.i_scoreboard.commit_ack_i[1] == 1'b1 && issue_stage_i.i_scoreboard.commit_pointer_q[1] == 2'd1) || (issue_stage_i.i_scoreboard.commit_ack_i[0] == 1'b1 && issue_stage_i.i_scoreboard.commit_pointer_q[0] == 2'd1)))  == 1'd0) && 
	 1'b1; 
wire scb_2_s12 = 
	(issue_stage_i.i_scoreboard.mem_q[2].sbe.pc == pc0) && 
	(issue_stage_i.i_scoreboard.mem_q[2].issued == 1'd1) && 
	(issue_stage_i.i_scoreboard.mem_q[2].sbe.valid == 1'd1) && 
	(issue_stage_i.i_scoreboard.mem_q[2].sbe.ex.valid == 1'd0) && 
	(((issue_stage_i.i_scoreboard.mem_n[2].issued == 1'b0) && ((issue_stage_i.i_scoreboard.commit_ack_i[1] == 1'b1 && issue_stage_i.i_scoreboard.commit_pointer_q[1] == 2'd2) || (issue_stage_i.i_scoreboard.commit_ack_i[0] == 1'b1 && issue_stage_i.i_scoreboard.commit_pointer_q[0] == 2'd2)))  == 1'd0) && 
	 1'b1; 
wire scb_2_s13 = 
	(issue_stage_i.i_scoreboard.mem_q[2].sbe.pc == pc0) && 
	(issue_stage_i.i_scoreboard.mem_q[2].issued == 1'd1) && 
	(issue_stage_i.i_scoreboard.mem_q[2].sbe.valid == 1'd1) && 
	(issue_stage_i.i_scoreboard.mem_q[2].sbe.ex.valid == 1'd0) && 
	(((issue_stage_i.i_scoreboard.mem_n[2].issued == 1'b0) && ((issue_stage_i.i_scoreboard.commit_ack_i[1] == 1'b1 && issue_stage_i.i_scoreboard.commit_pointer_q[1] == 2'd2) || (issue_stage_i.i_scoreboard.commit_ack_i[0] == 1'b1 && issue_stage_i.i_scoreboard.commit_pointer_q[0] == 2'd2)))  == 1'd1) && 
	 1'b1; 
wire scb_2_s14 = 
	(issue_stage_i.i_scoreboard.mem_q[2].sbe.pc == pc0) && 
	(issue_stage_i.i_scoreboard.mem_q[2].issued == 1'd1) && 
	(issue_stage_i.i_scoreboard.mem_q[2].sbe.valid == 1'd1) && 
	(issue_stage_i.i_scoreboard.mem_q[2].sbe.ex.valid == 1'd1) && 
	(((issue_stage_i.i_scoreboard.mem_n[2].issued == 1'b0) && ((issue_stage_i.i_scoreboard.commit_ack_i[1] == 1'b1 && issue_stage_i.i_scoreboard.commit_pointer_q[1] == 2'd2) || (issue_stage_i.i_scoreboard.commit_ack_i[0] == 1'b1 && issue_stage_i.i_scoreboard.commit_pointer_q[0] == 2'd2)))  == 1'd0) && 
	 1'b1; 
wire scb_2_s8 = 
	(issue_stage_i.i_scoreboard.mem_q[2].sbe.pc == pc0) && 
	(issue_stage_i.i_scoreboard.mem_q[2].issued == 1'd1) && 
	(issue_stage_i.i_scoreboard.mem_q[2].sbe.valid == 1'd0) && 
	(issue_stage_i.i_scoreboard.mem_q[2].sbe.ex.valid == 1'd0) && 
	(((issue_stage_i.i_scoreboard.mem_n[2].issued == 1'b0) && ((issue_stage_i.i_scoreboard.commit_ack_i[1] == 1'b1 && issue_stage_i.i_scoreboard.commit_pointer_q[1] == 2'd2) || (issue_stage_i.i_scoreboard.commit_ack_i[0] == 1'b1 && issue_stage_i.i_scoreboard.commit_pointer_q[0] == 2'd2)))  == 1'd0) && 
	 1'b1; 
wire scb_3_s12 = 
	(issue_stage_i.i_scoreboard.mem_q[3].sbe.pc == pc0) && 
	(issue_stage_i.i_scoreboard.mem_q[3].issued == 1'd1) && 
	(issue_stage_i.i_scoreboard.mem_q[3].sbe.valid == 1'd1) && 
	(issue_stage_i.i_scoreboard.mem_q[3].sbe.ex.valid == 1'd0) && 
	(((issue_stage_i.i_scoreboard.mem_n[3].issued == 1'b0) && ((issue_stage_i.i_scoreboard.commit_ack_i[1] == 1'b1 && issue_stage_i.i_scoreboard.commit_pointer_q[1] == 2'd3) || (issue_stage_i.i_scoreboard.commit_ack_i[0] == 1'b1 && issue_stage_i.i_scoreboard.commit_pointer_q[0] == 2'd3)))  == 1'd0) && 
	 1'b1; 
wire scb_3_s13 = 
	(issue_stage_i.i_scoreboard.mem_q[3].sbe.pc == pc0) && 
	(issue_stage_i.i_scoreboard.mem_q[3].issued == 1'd1) && 
	(issue_stage_i.i_scoreboard.mem_q[3].sbe.valid == 1'd1) && 
	(issue_stage_i.i_scoreboard.mem_q[3].sbe.ex.valid == 1'd0) && 
	(((issue_stage_i.i_scoreboard.mem_n[3].issued == 1'b0) && ((issue_stage_i.i_scoreboard.commit_ack_i[1] == 1'b1 && issue_stage_i.i_scoreboard.commit_pointer_q[1] == 2'd3) || (issue_stage_i.i_scoreboard.commit_ack_i[0] == 1'b1 && issue_stage_i.i_scoreboard.commit_pointer_q[0] == 2'd3)))  == 1'd1) && 
	 1'b1; 
wire scb_3_s14 = 
	(issue_stage_i.i_scoreboard.mem_q[3].sbe.pc == pc0) && 
	(issue_stage_i.i_scoreboard.mem_q[3].issued == 1'd1) && 
	(issue_stage_i.i_scoreboard.mem_q[3].sbe.valid == 1'd1) && 
	(issue_stage_i.i_scoreboard.mem_q[3].sbe.ex.valid == 1'd1) && 
	(((issue_stage_i.i_scoreboard.mem_n[3].issued == 1'b0) && ((issue_stage_i.i_scoreboard.commit_ack_i[1] == 1'b1 && issue_stage_i.i_scoreboard.commit_pointer_q[1] == 2'd3) || (issue_stage_i.i_scoreboard.commit_ack_i[0] == 1'b1 && issue_stage_i.i_scoreboard.commit_pointer_q[0] == 2'd3)))  == 1'd0) && 
	 1'b1; 
wire scb_3_s8 = 
	(issue_stage_i.i_scoreboard.mem_q[3].sbe.pc == pc0) && 
	(issue_stage_i.i_scoreboard.mem_q[3].issued == 1'd1) && 
	(issue_stage_i.i_scoreboard.mem_q[3].sbe.valid == 1'd0) && 
	(issue_stage_i.i_scoreboard.mem_q[3].sbe.ex.valid == 1'd0) && 
	(((issue_stage_i.i_scoreboard.mem_n[3].issued == 1'b0) && ((issue_stage_i.i_scoreboard.commit_ack_i[1] == 1'b1 && issue_stage_i.i_scoreboard.commit_pointer_q[1] == 2'd3) || (issue_stage_i.i_scoreboard.commit_ack_i[0] == 1'b1 && issue_stage_i.i_scoreboard.commit_pointer_q[0] == 2'd3)))  == 1'd0) && 
	 1'b1; 
wire stb_com_0_s1 = 
	(ex_stage_i.lsu_i.i_store_unit.store_buffer_i.commit_queue_q[0].pc == pc0) && 
	(ex_stage_i.lsu_i.i_store_unit.store_buffer_i.commit_queue_q[0].valid == 1'd1) && 
	 1'b1; 
wire stb_com_1_s1 = 
	(ex_stage_i.lsu_i.i_store_unit.store_buffer_i.commit_queue_q[1].pc == pc0) && 
	(ex_stage_i.lsu_i.i_store_unit.store_buffer_i.commit_queue_q[1].valid == 1'd1) && 
	 1'b1; 
wire stb_spec_0_s1 = 
	(ex_stage_i.lsu_i.i_store_unit.store_buffer_i.speculative_queue_q[0].pc == pc0) && 
	(ex_stage_i.lsu_i.i_store_unit.store_buffer_i.speculative_queue_q[0].valid == 1'd1) && 
	 1'b1; 
wire stb_spec_1_s1 = 
	(ex_stage_i.lsu_i.i_store_unit.store_buffer_i.speculative_queue_q[1].pc == pc0) && 
	(ex_stage_i.lsu_i.i_store_unit.store_buffer_i.speculative_queue_q[1].valid == 1'd1) && 
	 1'b1; 
wire load_unit_s1 = 
	(ex_stage_i.lsu_i.i_load_unit.load_data_q.ld_pc == pc0) && 
	(ex_stage_i.lsu_i.i_load_unit.valid_o == 1'd1) && 
	 1'b1; 
wire store_unit_s1 = 
	(ex_stage_i.lsu_i.i_store_unit.st_pc_q == pc0) && 
	(ex_stage_i.lsu_i.i_store_unit.state_q == 2'd1) && 
	 1'b1; 
wire store_unit_s3 = 
	(ex_stage_i.lsu_i.i_store_unit.st_pc_q == pc0) && 
	(ex_stage_i.lsu_i.i_store_unit.state_q == 2'd3) && 
	 1'b1; 
wire load_unit_buff_s1 = 
	(ex_stage_i.lsu_i.load_pc_o == pc0) && 
	(ex_stage_i.lsu_i.load_valid_o == 1'd1) && 
	 1'b1; 
wire csr_buffer_s1 = 
	(ex_stage_i.csr_buffer_i.csr_reg_q.pc == pc0) && 
	(ex_stage_i.csr_buffer_i.csr_reg_q.valid == 1'd1) && 
	 1'b1; 
wire mult_s1 = 
	(ex_stage_i.i_mult.i_multiplier.pc_q == pc0) && 
	(ex_stage_i.i_mult.i_multiplier.mult_valid_q == 1'd1) && 
	 1'b1; 
wire load_unit_op_s1 = 
	(ex_stage_i.lsu_i.i_load_unit.lsu_ctrl_i.pc == pc0) && 
	(ex_stage_i.lsu_i.i_load_unit.valid_i == 1'd1) && 
	(ex_stage_i.lsu_i.i_load_unit.state_q == 4'd1) && 
	 1'b1; 
wire load_unit_op_s2 = 
	(ex_stage_i.lsu_i.i_load_unit.lsu_ctrl_i.pc == pc0) && 
	(ex_stage_i.lsu_i.i_load_unit.valid_i == 1'd1) && 
	(ex_stage_i.lsu_i.i_load_unit.state_q == 4'd2) && 
	 1'b1; 
wire load_unit_op_s3 = 
	(ex_stage_i.lsu_i.i_load_unit.lsu_ctrl_i.pc == pc0) && 
	(ex_stage_i.lsu_i.i_load_unit.valid_i == 1'd1) && 
	(ex_stage_i.lsu_i.i_load_unit.state_q == 4'd3) && 
	 1'b1; 
wire mem_req_s1 = 
	(ex_stage_i.lsu_i.i_ord_sram.pc_i == pc0) && 
	(ex_stage_i.lsu_i.i_ord_sram.req_i == 1'd1) && 
	 1'b1; 

// TODO: use this for general case
wire in_perf_locs = serdiv_unit_divide_s1 ||
										serdiv_unit_divide_s2 ||
										id_stage_s1 ||
										issue_s1 ||
										issue_s2 ||
										issue_s8 ||
										issue_s16 ||
										issue_s32 ||
										lsq_enq_0_s1 ||
										lsq_enq_1_s1 ||
										scb_0_s12 ||
										scb_0_s13 ||
										scb_0_s14 ||
										scb_0_s8 ||
										scb_1_s12 ||
										scb_1_s13 ||
										scb_1_s14 ||
										scb_1_s8 ||
										scb_2_s12 ||
										scb_2_s13 ||
										scb_2_s14 ||
										scb_2_s8 ||
										scb_3_s12 ||
										scb_3_s13 ||
										scb_3_s14 ||
										scb_3_s8 ||
										stb_com_0_s1 ||
										stb_com_1_s1 ||
										stb_spec_0_s1 ||
										stb_spec_1_s1 ||
										load_unit_s1 ||
										store_unit_s1 ||
										store_unit_s3 ||
										load_unit_buff_s1 ||
										csr_buffer_s1 ||
										mult_s1 ||
										load_unit_op_s1 ||
										load_unit_op_s2 ||
										load_unit_op_s3 ||
										mem_req_s1;

reg prev_in_perf_locs; 

always_ff @(posedge clk_i) begin
	if (!rst_ni) begin
		prev_in_perf_locs <= 1'b0;
	end else begin
		prev_in_perf_locs <= in_perf_locs;
	end
end
