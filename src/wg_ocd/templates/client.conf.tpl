[Interface]
PrivateKey = ${client_private_key}
Address = ${client_address}
DNS = ${dns}

[Peer]
PublicKey = ${server_public_key}
Endpoint = ${endpoint}
AllowedIPs = ${allowed_ips}
PersistentKeepalive = 25
