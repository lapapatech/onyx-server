#!/usr/bin/env bash
# ⬡ Onyx CLI — One-liner installer
# curl -sSL https://onyx.devnullbox.net/install.sh | bash
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

ONYX_BACKEND="${ONYX_BACKEND:-https://onyx.devnullbox.net}"
ONYX_VERSION="${ONYX_VERSION:-latest}"

echo -e "${CYAN}${BOLD}"
echo "   ⬡ Onyx CLI Installer"
echo -e "${NC}"
echo ""

# ── Check Node.js ─────────────────────────────────────────
require_node() {
    if ! command -v node &>/dev/null; then
        echo -e "${RED}Node.js is not installed.${NC}"
        echo ""
        echo "Install Node.js 22+ first:"
        echo "  curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -"
        echo "  sudo apt-get install -y nodejs"
        echo ""
        echo "Or via nvm:"
        echo "  curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash"
        echo "  nvm install 22"
        exit 1
    fi
    local node_ver
    node_ver=$(node -v | sed 's/v//' | cut -d. -f1)
    if [ "$node_ver" -lt 22 ]; then
        echo -e "${RED}Node.js 22+ required. Current: $(node -v)${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓${NC} Node $(node -v)"
}

require_node

# ── Install Onyx ───────────────────────────────────────────
echo -e "${CYAN}Installing Onyx CLI...${NC}"

if command -v onyx &>/dev/null; then
    current_ver=$(onyx --version 2>/dev/null || echo "unknown")
    echo -e "  Onyx already installed ($current_ver), updating..."
    npm install -g @onyxhq/onyx@${ONYX_VERSION} --silent 2>/dev/null || true
else
    npm install -g @onyxhq/onyx@${ONYX_VERSION} --silent 2>/dev/null || {
        echo -e "${RED}npm install failed. Trying with --force...${NC}"
        npm install -g @onyxhq/onyx@${ONYX_VERSION} --force
    }
fi

echo -e "${GREEN}✓${NC} Onyx CLI installed"

# ── Configure ──────────────────────────────────────────────
ONYX_DIR="${HOME}/.onyx"
mkdir -p "${ONYX_DIR}"

SETTINGS_FILE="${ONYX_DIR}/settings.json"

if [ ! -f "${SETTINGS_FILE}" ]; then
    # Register a free API key
    echo -e "${CYAN}Getting your API key...${NC}"
    API_KEY=""
    if command -v curl &>/dev/null; then
        REG_RESP=$(curl -s --max-time 10 "${ONYX_BACKEND}/v1/auth/register" \
            -H "Content-Type: application/json" \
            -d '{"name":"'"$(whoami)@$(hostname)"'"}' 2>/dev/null || echo "")
        # Try python3 first, then node (both parse JSON)
        if command -v python3 &>/dev/null; then
            API_KEY=$(echo "$REG_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('api_key',''))" 2>/dev/null || echo "")
        elif command -v node &>/dev/null; then
            API_KEY=$(echo "$REG_RESP" | node -e "process.stdin.on('data',d=>{try{console.log(JSON.parse(d).api_key||'')}catch(e){console.log('')}})" 2>/dev/null || echo "")
        fi
    fi

    if [ -n "$API_KEY" ]; then
        echo -e "${GREEN}✓${NC} API key obtained: ${API_KEY:0:20}..."
    else
        echo ""
        echo -e "${RED}${BOLD}⚠ Could not auto-register your API key${NC}"
        echo ""
        echo "  This happens if python3 or curl is not available."
        echo "  Get your key manually (it's free and instant):"
        echo ""
        echo -e "    ${BOLD}curl ${ONYX_BACKEND}/v1/auth/register \\"
        echo "      -H 'Content-Type: application/json' \\"
        echo -e "      -d '{\"name\":\"\$(whoami)@\$(hostname)\"}'${NC}"
        echo ""
        echo "  Then add the key to ${SETTINGS_FILE}:"
        echo -e "    ${BOLD}security.auth.apiKey${NC}"
        echo ""
        API_KEY=""
    fi

    cat > "${SETTINGS_FILE}" <<EOF
{
  "security": {
    "auth": {
      "selectedType": "openai",
      "apiKey": "${API_KEY}",
      "baseUrl": "${ONYX_BACKEND}/v1"
    }
  },
  "model": "onyx-flash",
  "\$version": 4
}
EOF
    echo -e "${GREEN}✓${NC} Created ${SETTINGS_FILE}"
else
    # Update baseUrl if it exists in security.auth
    if command -v python3 &>/dev/null; then
        python3 -c "
import json, os
f = '${SETTINGS_FILE}'
d = json.load(open(f))
# Handle both old and new format
if 'security' in d and 'auth' in d.get('security', {}):
    d['security']['auth']['baseUrl'] = '${ONYX_BACKEND}/v1'
else:
    d['security'] = {'auth': {'selectedType': 'openai', 'baseUrl': '${ONYX_BACKEND}/v1'}}
d['\$version'] = 4
json.dump(d, open(f, 'w'), indent=2)
print('✓ Updated settings')
" 2>/dev/null || true
    fi
    echo -e "${GREEN}✓${NC} Settings file exists, updated"
fi

# ── Verify ─────────────────────────────────────────────────
echo ""
echo -e "${BOLD}Verifying installation...${NC}"

if command -v onyx &>/dev/null; then
    ONYX_PATH=$(which onyx)
    echo -e "${GREEN}✓${NC} onyx binary: ${ONYX_PATH}"
else
    echo -e "${RED}✗ onyx not found in PATH${NC}"
    echo "  Try: export PATH=\"\$PATH:\$(npm bin -g)\""
    exit 1
fi

# Test backend connectivity
if command -v curl &>/dev/null; then
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "${ONYX_BACKEND}/health" 2>/dev/null || echo "000")
    if [ "$HTTP_CODE" = "200" ]; then
        echo -e "${GREEN}✓${NC} Backend reachable: ${ONYX_BACKEND}"
    else
        echo -e "${RED}✗ Backend unreachable (HTTP ${HTTP_CODE}): ${ONYX_BACKEND}${NC}"
    fi
fi

echo ""
echo -e "${GREEN}${BOLD}⬡ Onyx is ready!${NC}"
echo ""
echo "  Start a session:"
echo -e "    ${BOLD}onyx${NC}"
echo ""
echo "  Get an API key:"
echo -e "    ${BOLD}curl -s ${ONYX_BACKEND}/v1/auth/register${NC}"
echo ""
