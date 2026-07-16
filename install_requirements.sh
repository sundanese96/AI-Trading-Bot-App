#!/bin/bash
set -e

# ANSI Color Codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Memulai Pemasangan Dependensi KriptoSakti Simulator ===${NC}"
echo -e "${YELLOW}Deteksi Sistem Operasi...${NC}"

# Check OS compatibility (Ubuntu/Debian)
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$NAME
    VER=$VERSION_ID
else
    OS=$(uname -s)
    VER=""
fi

echo -e "Sistem Operasi: ${GREEN}$OS ($VER)${NC}"

# Ensure package lists are updated if we need to install dependencies
update_apt() {
    echo -e "${YELLOW}Melakukan apt-get update...${NC}"
    sudo apt-get update
}

# 1. Check Python3, pip, and venv
echo -e "\n${GREEN}[1/3] Memeriksa Python & Virtual Environment...${NC}"
NEED_APT_UPDATE=0

if ! command -v python3 &> /dev/null; then
    echo -e "${YELLOW}Python3 tidak ditemukan. Memasang Python3...${NC}"
    NEED_APT_UPDATE=1
fi

if ! dpkg -l | grep -q "python3-pip"; then
    echo -e "${YELLOW}python3-pip tidak ditemukan. Memasang pip...${NC}"
    NEED_APT_UPDATE=1
fi

if ! dpkg -l | grep -q "python3-venv"; then
    echo -e "${YELLOW}python3-venv tidak ditemukan. Memasang venv...${NC}"
    NEED_APT_UPDATE=1
fi

if [ $NEED_APT_UPDATE -eq 1 ]; then
    update_apt
    echo -e "${YELLOW}Memasang paket Python (python3, python3-pip, python3-venv)...${NC}"
    sudo apt-get install -y python3 python3-pip python3-venv
else
    echo -e "${GREEN}Python3, pip, dan venv sudah terpasang.${NC}"
fi

# 2. Setup Python Virtual Environment and Install backend dependencies
echo -e "\n${GREEN}[2/3] Mengonfigurasi Virtual Environment Python...${NC}"
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Membuat virtual environment baru di './venv'...${NC}"
    python3 -m venv venv
else
    echo -e "${GREEN}Virtual environment './venv' sudah ada.${NC}"
fi

echo -e "${YELLOW}Mengaktifkan virtual environment & memperbarui pip...${NC}"
source venv/bin/activate
pip install --upgrade pip

if [ -f "backend/requirements.txt" ]; then
    echo -e "${YELLOW}Memasang dependensi Python dari 'backend/requirements.txt'...${NC}"
    pip install -r backend/requirements.txt
    echo -e "${GREEN}Dependensi Python berhasil dipasang.${NC}"
else
    echo -e "${RED}Peringatan: backend/requirements.txt tidak ditemukan. Lewati pemasangan pip.${NC}"
fi
deactivate

# 3. Check NodeJS and NPM
echo -e "\n${GREEN}[3/3] Memeriksa Node.js & NPM...${NC}"
INSTALL_NODE=0

if ! command -v node &> /dev/null; then
    echo -e "${YELLOW}Node.js tidak ditemukan. Memasang Node.js...${NC}"
    INSTALL_NODE=1
fi

if ! command -v npm &> /dev/null; then
    echo -e "${YELLOW}NPM tidak ditemukan. Memasang NPM...${NC}"
    INSTALL_NODE=1
fi

if [ $INSTALL_NODE -eq 1 ]; then
    # Ensure curl is installed
    if ! command -v curl &> /dev/null; then
        echo -e "${YELLOW}Memasang curl untuk mengunduh NodeSource...${NC}"
        sudo apt-get install -y curl
    fi
    echo -e "${YELLOW}Menyiapkan repositori NodeSource Node.js v20.x...${NC}"
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    echo -e "${YELLOW}Memasang Node.js & NPM...${NC}"
    sudo apt-get install -y nodejs
else
    echo -e "${GREEN}Node.js ($(node -v)) dan NPM ($(npm -v)) sudah terpasang.${NC}"
fi

# Install JS/React frontend dependencies
if [ -f "package.json" ]; then
    echo -e "${YELLOW}Memasang dependensi JavaScript (node_modules)...${NC}"
    npm install
    echo -e "${GREEN}Dependensi JavaScript berhasil dipasang.${NC}"
else
    echo -e "${RED}Peringatan: package.json tidak ditemukan. Lewati npm install.${NC}"
fi

echo -e "\n${GREEN}=== Pemasangan Dependensi Selesai dengan Sukses! ===${NC}"
echo -e "Gunakan perintah berikut untuk memulai aplikasi:"
echo -e "  ${YELLOW}./run_project.sh${NC}"
echo -e "========================================================\n"
