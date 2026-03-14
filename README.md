# SynthEC

Step 1:

To run SynthEC, first run steps 0, 1 below. When you run the scripts, you may have to `source` them rather than just using `./`. 

Step 2:

After running those setup scripts, navigate to `fv/synthlc`. There, you should run 

```
./run_synthec_demo.sh AND.sv
```

This should launch a JG session evaluating all the instructions for the general flush case.  

Step 3: 

Sorry this is gross! But go into `fv/synthlc/xSquashDetect/squash_detect_setup.py`. 

Search for "Step 3" instructions there. Comment the general case out, uncomment out the specific checks, and then add which instructions that was found to be able to cause a general flush. The if statement is pre-populated with our findings. 

Then run the synthec demo command again. 

Step 4: 

Another gross step sorry! But now go into `fv/src/header_squash.sv`. Search for "Step 4" instructions there. Uncomment that assumption and adjust N. This is to find the window of the contract. 

Then run the synthec demo command again.

# Artifact Evaluation: 
1. [00-installation](./00-installation.md)
2. [01-setup](./01-setup.md)
3. [02-duvpl-dfg](./02-duvpl-dfg.md)
4. [03-rtl2mupath](./03-rtl2mupath.md)
5. [04-synthlc](./04-synthlc.md)
6. [05-5instn-isa](./05-5instn-isa.md)
7. [06-lc-table](./06-lc-table.md)

## Supplementary Materials 
* Synthesized upaths for all instructions in html: [here](./index.html)
* Formal proof: [supplementary.pdf](./supplementary.pdf)
