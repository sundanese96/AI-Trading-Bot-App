#!/bin/sh
set -e

# ANSI Color Codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

printf "${GREEN}=== Memulai Pemasangan Dependensi KriptoSakti Simulator ===${NC}\n"
printf "${YELLOW}Deteksi Sistem Operasi...${NC}\n"

# Check OS compatibility (Ubuntu/Debian)
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$NAME
    VER=$VERSION_ID
else
    OS=$(uname -s)
    VER=""
fi

printf "Sistem Operasi: ${GREEN}%s (%s)${NC}\n" "$OS" "$VER"

# Ensure package lists are updated if we need to install dependencies
update_apt() {
    printf "${YELLOW}Melakukan apt-get update...${NC}\n"
    sudo apt-get update
}

# 1. Check Python3, pip, and venv
printf "\n${GREEN}[1/3] Memeriksa Python & Virtual Environment...${NC}\n"
NEED_APT_UPDATE=0

if ! command -v python3 > /dev/null 2>&1; then
    printf "${YELLOW}Python3 tidak ditemukan. Memasang Python3...${NC}\n"
    NEED_APT_UPDATE=1
fi

if ! dpkg -l | grep -q "python3-pip"; then
    printf "${YELLOW}python3-pip tidak ditemukan. Memasang pip...${NC}\n"
    NEED_APT_UPDATE=1
fi

if ! dpkg -l | grep -q "python3-venv"; then
    printf "${YELLOW}python3-venv tidak ditemukan. Memasang venv...${NC}\n"
    NEED_APT_UPDATE=1
fi

if [ $NEED_APT_UPDATE -eq 1 ]; then
    update_apt
    printf "${YELLOW}Memasang paket Python (python3, python3-pip, python3-venv)...${NC}\n"
    sudo apt-get install -y python3 python3-pip python3-venv
else
    printf "${GREEN}Python3, pip, dan venv sudah terpasang.${NC}\n"
fi

# 2. Setup Python Virtual Environment and Install backend dependencies
printf "\n${GREEN}[2/3] Mengonfigurasi Virtual Environment Python...${NC}\n"
if [ ! -d "venv" ]; then
    printf "${YELLOW}Membuat virtual environment baru di './venv'...${NC}\n"
    python3 -m venv venv
else
    printf "${GREEN}Virtual environment './venv' sudah ada.${NC}\n"
fi

printf "${YELLOW}Mengaktifkan virtual environment & memperbarui pip...${NC}\n"
. venv/bin/activate
pip install --upgrade pip

if [ -f "backend/requirements.txt" ]; then
    printf "${YELLOW}Memasang dependensi Python dari 'backend/requirements.txt'...${NC}\n"
    pip install -r backend/requirements.txt
    printf "${GREEN}Dependensi Python berhasil dipasang.${NC}\n"
else
    printf "${RED}Peringatan: backend/requirements.txt tidak ditemukan. Lewati pemasangan pip.${NC}\n"
fi
deactivate

# 3. Check NodeJS and NPM
printf "\n${GREEN}[3/3] Memeriksa Node.js & NPM...${NC}\n"
INSTALL_NODE=0

if ! command -v node > /dev/null 2>&1; then
    printf "${YELLOW}Node.js tidak ditemukan. Memasang Node.js...${NC}\n"
    INSTALL_NODE=1
fi

if ! command -v npm > /dev/null 2>&1; then
    printf "${YELLOW}NPM tidak ditemukan. Memasang NPM...${NC}\n"
    INSTALL_NODE=1
fi

if [ $INSTALL_NODE -eq 1 ]; then
    # Ensure curl is installed
    if ! command -v curl > /dev/null 2>&1; then
        printf "${YELLOW}Memasang curl untuk mengunduh NodeSource...${NC}\n"
        sudo apt-get install -y curl
    fi
    printf "${YELLOW}Menyiapkan repositori NodeSource Node.js v20.x...${NC}\n"
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    printf "${YELLOW}Memasang Node.js & NPM...${NC}\n"
    sudo apt-get install -y nodejs
else
    printf "${GREEN}Node.js (%s) dan NPM (%s) sudah terpasang.${NC}\n" "$(node -v)" "$(npm -v)"
fi

# Install JS/React frontend dependencies
if [ -f "package.json" ]; then
    printf "${YELLOW}Memasang dependensi JavaScript (node_modules)...${NC}\n"
    npm install
    printf "${GREEN}Dependensi JavaScript berhasil dipasang.${NC}\n"
else
    printf "${RED}Peringatan: package.json tidak ditemukan. Lewati npm install.${NC}\n"
fi

printf "\n${GREEN}=== Pemasangan Dependensi Selesai dengan Sukses! ===${NC}\n"
printf "Gunakan perintah berikut untuk memulai aplikasi:\n"
printf "  ${YELLOW}./run_project.sh${NC}\n"
printf "========================================================\n\n"
