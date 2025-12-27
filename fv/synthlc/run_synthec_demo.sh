#!/usr/bin/bash
# non-interference case
# heuristic only handle undetermined cases line 435
set -e 
set -o pipefail

PWD=$(pwd)
PWD_PREFIX=$(basename ${PWD})
# assumption/opcode for the instn
INSTNDIR=opcodes_gen_all
# run over all
INSTN_FILES=$(ls $INSTNDIR)
fnm=DIV.sv
if [ -z $1 ];
then
    echo "Pass an argument such as as \`./run_an_instn_demo_ift.sh LW.sv\`"
    exit
else
    echo "===> Processing: $1"
    fnm="$1"
fi

# This folder name
SYNTHLCFOLD=$(basename $(pwd))


filename=$(basename $fnm)
fileprefix="${filename%.*}"

INAME="i_${fileprefix}_out" 
echo "${fnm}"

INSTN="$INSTNDIR/$fnm"
echo "=========== INSTN ============="
echo "- Directory: $INAME"
echo "- Instruction file: $INSTN"
cat $INSTN
echo "==============================="

if [ ! -d "$INAME" ]; then 
    echo "Directory does not exists $INAME"
    exit 0
fi
cp $INSTN $INAME/idef.sv

cd $INAME

########## 
## STEP 1 
########## 
echo "
================================================================================
STEP 1 at $(pwd) $(date)
================================================================================
"

DIR=xSquashDetect
PYSCRPT=squash_detect_setup

# TODO REMOVE
if [ -d "${DIR}" ]; then 
    rm -r ${DIR}
fi

cp -r ../${DIR} .
cd ${DIR}
python3 ${PYSCRPT}.py

cd ../../../

./RUN_JG.sh -j ./$SYNTHLCFOLD/$INAME/${DIR} -s ./$SYNTHLCFOLD/$INAME/${DIR}/squash_detect.sv -t ./$SYNTHLCFOLD/$INAME/${DIR}/squash_detect.tcl --spv -g 1

# TODO REMOVE

# if [ -d "${DIR}" ]; then 
#     echo "Directory exists ${DIR} and do only post-proc step"
# else 
#     cp -r ../${DIR} .
#     cd ${DIR}
#     python3 ${PYSCRPT}.py
# fi
