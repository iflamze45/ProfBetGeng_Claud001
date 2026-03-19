#!/bin/bash
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
nvm use 20 > /dev/null 2>&1
cd /Users/alexanderanthony/Projects/ProfBetGeng_Claud001/frontend
exec npx vite --host --port 5173
