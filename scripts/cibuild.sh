#!/bin/bash

# Output a line prefixed with a timestamp
info()
{
	echo "$(date +'%F %T') |"
}

# Track number of seconds required to run script
START=$(date +%s)
echo "$(info) starting build checks."

# invoke defaults to running tests in a docker container for travis we want to execute them locally
export INVOKE_NAUTOBOT_INVOKE_LOCAL=True

# Syntax check all python source files
SYNTAX=$(find . -name "*.py" -type f -exec python -m py_compile {} \; 2>&1)
if [[ ! -z $SYNTAX ]]; then
	echo -e "$SYNTAX"
	echo -e "\n$(info) detected one or more syntax errors; failing build."
	exit 1
fi

# Run Nautobot tests
invoke unittest --failfast
RC=$?
if [[ $RC != 0 ]]; then
	echo -e "\n$(info) one or more tests failed, failing build."
	exit $RC
fi

# Show code coverage report
invoke unittest-coverage
RC=$?
if [[ $RC != 0 ]]; then
	echo -e "\n$(info) failed to generate code coverage report."
	exit $RC
fi

# Show build duration
END=$(date +%s)
echo "$(info) exiting after $(($END - $START)) seconds."

exit 0
