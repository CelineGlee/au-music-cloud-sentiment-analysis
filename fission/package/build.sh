#!/bin/sh
echo "SRC_PKG is set to: $SRC_PKG"
echo "DEPLOY_PKG is set to: $DEPLOY_PKG"
echo "Dependencies:"
cat ${SRC_PKG}/requirements.txt
echo "----"
echo "src contents:"
echo "$(ls -l ${SRC_PKG})"
echo "----"
pip3 install -r ${SRC_PKG}/requirements.txt -t ${SRC_PKG} && cp -r ${SRC_PKG} ${DEPLOY_PKG}
echo "----"
echo "deploy contents:"
echo "$(ls -l ${DEPLOY_PKG})"
echo "----"