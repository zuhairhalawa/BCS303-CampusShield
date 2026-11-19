# Kali Linux lab image for CampusShield (official kali-rolling base + the lab tools)
FROM kalilinux/kali-rolling
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      nmap tshark sqlite3 curl iptables iproute2 openssl netcat-openbsd iputils-ping \
      procps util-linux passwd ca-certificates \
      python3 python3-flask python3-cryptography python3-requests \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /lab
