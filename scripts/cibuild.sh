#!/bin/bash

# Exit code starts at 0 but is modified if any checks fail
EXIT=0

# Output a line prefixed with a timestamp
info()
{
	echo "$(date +'%F %T') |"
}

# Track number of seconds required to run script
START=$(date +%s)
echo "$(info) starting build checks."

# Syntax check all python source files
SYNTAX=$(find . -name "*.py" -type f -exec python -m py_compile {} \; 2>&1)
if [[ ! -z $SYNTAX ]]; then
	echo -e "$SYNTAX"
	echo -e "\n$(info) detected one or more syntax errors; failing build."
	EXIT=1
fi

# Check all built-in python source files for PEP 8 compliance
flake8 development/ nautobot/ tasks.py
RC=$?
if [[ $RC != 0 ]]; then
	echo -e "\n$(info) one or more PEP 8 errors detected; failing build."
	EXIT=$RC
fi

# Check that all files conform to Black.
black --check development/ nautobot/ tasks.py
RC=$?
if [[ $RC != 0 ]]; then
	echo -e "\n$(info) one or more Black errors detected; failing build."
	EXIT=$RC
fi

# Point to the testing nautobot_config file for use in CI
TEST_CONFIG=nautobot/core/tests/nautobot_config.py

# Run Nautobot tests
coverage run -m nautobot.core.cli --config=$TEST_CONFIG test nautobot/
RC=$?
if [[ $RC != 0 ]]; then
	echo -e "\n$(info) one or more tests failed, failing build."
	EXIT=$RC
fi

# Show code coverage report
coverage report --skip-covered --include "nautobot/*" --omit "*migrations*"
RC=$?
if [[ $RC != 0 ]]; then
	echo -e "\n$(info) failed to generate code coverage report."
	EXIT=$RC
fi

# Show build duration
END=$(date +%s)
echo "$(info) exiting with code $EXIT after $(($END - $START)) seconds."

exit $EXIT
