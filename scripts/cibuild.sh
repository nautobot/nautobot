#!/bin/bash

# Output a line prefixed with a timestamp
info()
{
	echo "$(date +'%F %T') |"
}

# Track number of seconds required to run script
START=$(date +%s)
echo "$(info) Starting build checks..."

# invoke defaults to running tests in a docker container for travis we want to execute them locally
export INVOKE_NAUTOBOT_LOCAL=True

echo -e "\n>> Checking that there aren't any missing or failing migrations..."
invoke check-migrations
RC=$?
if [[ $RC != 0 ]]; then
	echo -e "\n$(info) one or more Django migration errors detected; failing build."
	exit $RC
fi

echo -e "\n>> Checking that Python files conform to Black..."
invoke black
RC=$?
if [[ $RC != 0 ]]; then
	echo -e "\n$(info) one or more Black errors detected; failing build."
	exit $RC
fi

echo -e "\n>> Checking that Python files confirm to PEP 8..."
invoke flake8
RC=$?
if [[ $RC != 0 ]]; then
	echo -e "\n$(info) one or more PEP 8 errors detected; failing build."
	exit $RC
fi

echo -e "\n>> Checking syntax of Python files..."
SYNTAX=$(find . -name "*.py" -type f -exec python -m py_compile {} \; 2>&1)
if [[ ! -z $SYNTAX ]]; then
	echo -e "$SYNTAX"
	echo -e "\n$(info) detected one or more syntax errors; failing build."
	exit 1
fi

echo -e "\n>> Running unit tests..."
invoke unittest --failfast
RC=$?
if [[ $RC != 0 ]]; then
	echo -e "\n$(info) one or more tests failed, failing build."
	exit $RC
fi

echo -e "\n>> Displaying code coverage report..."
invoke unittest-coverage
RC=$?
if [[ $RC != 0 ]]; then
	echo -e "\n$(info) failed to generate code coverage report."
	exit $RC
fi

# Show build duration
END=$(date +%s)
echo "$(info) All checks passed after $(($END - $START)) seconds."

exit 0
