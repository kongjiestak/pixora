#!/bin/zsh
cd -- "${0:A:h}" || exit 1
python3 start_pixora.py "$@"
status_code=$?
if (( status_code != 0 )); then
  echo '启动未完成 / Startup did not complete. Press Enter to close.'
  read -r
fi
exit "$status_code"
