#!/bin/bash

TGT=$HOME/.local/tau
SRC=src

mkdir -p ${TGT}

rm -f ${TGT}/*
rm -rf ${TGT}/__pycache__
rm -f ${TGT}/tools/*
rm -rf ${TGT}/tools/__pycache__
rm -f ${TGT}/commands/*
rm -rf ${TGT}/commands/__pycache__
cp -r ${SRC}/* ${TGT}
chmod a+x ${TGT}/tau.py
# No renaming needed - tau.py is the final production file

# Add 'tau' alias to shell rc files (only if not already present)
TAU_ALIAS="alias tau='python3 ${TGT}/tau.py'"

for rcfile in "$HOME/.bashrc" "$HOME/.zshrc"; do
    if [ -f "$rcfile" ]; then
        if ! grep -q "alias tau=" "$rcfile" 2>/dev/null; then
            echo "" >> "$rcfile"
            echo "# TauErgon CLI alias" >> "$rcfile"
            echo "$TAU_ALIAS" >> "$rcfile"
            echo "Added 'tau' alias to $rcfile"
        fi
    fi
done
