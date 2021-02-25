#!/bin/bash
# This script will prepare Nautobot to run after the code has been upgraded to
# its most recent release.

export NAUTOBOT_CONFIG=/opt/nautobot/nautobot_config.py
NAUTOBOT_USER=nautobot

# Change to the directory where script is ran
cd "$(dirname "$0")"

STATIC_DIRS=(
    "jobs"
    "git"
    "media/image-attachments"
    "media/devicetype-images"
)

echo "Verifying static file directories..."
for d in "${STATIC_DIRS[@]}"; do
    STATIC_DIR="$(pwd -P)/$d"
    # echo $STATIC_DIR
    if [ ! -d "${STATIC_DIR}" ]; then
        echo "  Creating ${STATIC_DIR}..."
        mkdir -p $STATIC_DIR
        chown -R $NAUTOBOT_USER $STATIC_DIR
    fi
done

# Prep path to virtual environment
VIRTUALENV="$(pwd -P)/venv"

# Remove the existing virtual environment (if any)
if [ -d "$VIRTUALENV" ]; then
  COMMAND="rm -rf ${VIRTUALENV}"
  echo "Removing old virtual environment..."
  eval $COMMAND
else
  WARN_MISSING_VENV=1
fi

# Create a new virtual environment
COMMAND="/usr/bin/python3 -m venv ${VIRTUALENV}"
echo "Creating a new virtual environment at ${VIRTUALENV}..."
eval $COMMAND || {
  echo "--------------------------------------------------------------------"
  echo "ERROR: Failed to create the virtual environment. Check that you have"
  echo "the required system packages installed and the following path is"
  echo "writable: ${VIRTUALENV}"
  echo "--------------------------------------------------------------------"
  exit 1
}

# Activate the virtual environment
source "${VIRTUALENV}/bin/activate"

# Upgrade pip3
COMMAND="pip3 install --upgrade pip"
echo "Upgrading Python package installer ($COMMAND)..."
eval $COMMAND || exit 1

# Install necessary system packages
COMMAND="pip3 install wheel"
echo "Installing Python system packages ($COMMAND)..."
eval $COMMAND || exit 1

# Install required Python packages
COMMAND="pip3 install nautobot"
echo "Installing Nautobot and its dependencies ($COMMAND)..."
eval $COMMAND || exit 1

# Install optional packages (if any)
if [ -s "local_requirements.txt" ]; then
  COMMAND="pip3 install -r local_requirements.txt"
  echo "Installing local dependencies ($COMMAND)..."
  eval $COMMAND || exit 1
elif [ -f "local_requirements.txt" ]; then
  echo "Skipping local dependencies (local_requirements.txt is empty)"
else
  echo "Skipping local dependencies (local_requirements.txt not found)"
fi

# Apply any database migrations
COMMAND="nautobot-server migrate"
echo "Applying database migrations ($COMMAND)..."
eval $COMMAND || exit 1

# Trace any missing cable paths (not typically needed)
COMMAND="nautobot-server trace_paths --no-input"
echo "Checking for missing cable paths ($COMMAND)..."
eval $COMMAND || exit 1

# Collect static files
COMMAND="nautobot-server collectstatic --no-input"
echo "Collecting static files ($COMMAND)..."
eval $COMMAND || exit 1

# Delete any stale content types
COMMAND="nautobot-server remove_stale_contenttypes --no-input"
echo "Removing stale content types ($COMMAND)..."
eval $COMMAND || exit 1

# Delete any expired user sessions
COMMAND="nautobot-server clearsessions"
echo "Removing expired user sessions ($COMMAND)..."
eval $COMMAND || exit 1

# Clear all cached data
COMMAND="nautobot-server invalidate all"
echo "Clearing cache data ($COMMAND)..."
eval $COMMAND || exit 1

if [ -v WARN_MISSING_VENV ]; then
  echo "--------------------------------------------------------------------"
  echo "WARNING: No existing virtual environment was detected. A new one has"
  echo "been created. Update your systemd service files to reflect the new"
  echo "Python and gunicorn executables. (If this is a new installation,"
  echo "this warning can be ignored.)"
  echo ""
  echo "nautobot.service ExecStart:"
  echo "  ${VIRTUALENV}/bin/gunicorn"
  echo ""
  echo "nautobot-rq.service ExecStart:"
  echo "  ${VIRTUALENV}/bin/python"
  echo ""
  echo "After modifying these files, reload the systemctl daemon:"
  echo "  > systemctl daemon-reload"
  echo "--------------------------------------------------------------------"
fi

echo "Upgrade complete! Don't forget to restart the Nautobot services:"
echo "  > sudo systemctl restart nautobot nautobot-rq"
