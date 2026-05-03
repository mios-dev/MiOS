#!/usr/bin/bash
# generate-mok-key.sh — one-shot MiOS MOK key generator.
#
# Generates a 2048-bit RSA key (NOT 4096: shim compatibility) with:
#   - codeSigning EKU
#   - 1.3.6.1.5.5.7.3.3 (Standard Code Signing)
#   - 1.3.6.1.4.1.311.61.1.1 (MS Kernel Module Code Signing)
#   - 1.3.6.1.4.1.311.10.3.5 (WHQL Driver Verification)
#   - 10-year validity
#
# Output: /etc/pki/mios/mok.{priv,der,pem,pub.b64,sha256}
# Refuses to overwrite an existing key.
#
# Store the encrypted private key in GitHub secret MIOS_MOK_KEY_B64
# and the passphrase in MIOS_MOK_KEY_PASSWORD. Never regenerate per-build.
set -euo pipefail

KEY_DIR=/etc/pki/mios
PRIV_KEY="${KEY_DIR}/mok.priv"
DER_CERT="${KEY_DIR}/mok.der"
PEM_CERT="${KEY_DIR}/mok.pem"
B64_PRIV="${KEY_DIR}/mok.priv.b64"
SHA256_OUT="${KEY_DIR}/mok.sha256"

if [[ -f "$DER_CERT" ]]; then
    echo "ERROR: $DER_CERT already exists. MOK keys are generated once."
    echo "If you need to rotate, delete the old key files first, re-enroll with mokutil,"
    echo "and then re-run this script."
    exit 1
fi

if [[ "$(id -u)" -ne 0 ]]; then
    echo "ERROR: run as root (sudo automation/generate-mok-key.sh)"
    exit 1
fi

install -d -m 0700 "$KEY_DIR"

echo "MiOS MOK key generation — 2048-bit RSA, 10-year validity."
echo "Set passphrase prompt: store in GitHub secret MIOS_MOK_KEY_PASSWORD."

# Create EKU extension config
EXTFILE=$(mktemp /tmp/mok-ext.XXXXXX.conf)
cat >"$EXTFILE" <<'EOF'
[req]
default_bits       = 2048
default_md         = sha256
distinguished_name = dn
x509_extensions    = v3_ca
prompt             = no

[dn]
CN = MiOS Module Signing Key

[v3_ca]
basicConstraints       = CA:FALSE
keyUsage               = digitalSignature
extendedKeyUsage       = codeSigning, 1.3.6.1.5.5.7.3.3, 1.3.6.1.4.1.311.61.1.1, 1.3.6.1.4.1.311.10.3.5
subjectKeyIdentifier   = hash
authorityKeyIdentifier = keyid:always
EOF

# Generate encrypted key + self-signed cert
openssl req \
    -newkey rsa:2048 \
    -nodes \
    -keyout "${PRIV_KEY}.plain" \
    -x509 \
    -outform PEM \
    -out "$PEM_CERT" \
    -days 3650 \
    -config "$EXTFILE"

# Convert cert to DER (the format mokutil needs)
openssl x509 -in "$PEM_CERT" -outform DER -out "$DER_CERT"

# Encrypt the private key
echo "Enter passphrase to encrypt the private key (for GitHub secret storage):"
openssl pkcs8 -topk8 -inform PEM -outform PEM \
    -in "${PRIV_KEY}.plain" \
    -out "$PRIV_KEY"
rm -f "${PRIV_KEY}.plain"

# Base64-encode encrypted PEM for GitHub secret
base64 -w0 "$PRIV_KEY" > "$B64_PRIV"

# SHA-256 fingerprint of the DER cert
FINGERPRINT=$(openssl x509 -inform DER -in "$DER_CERT" -fingerprint -sha256 -noout | sed 's/.*=//')
echo "$FINGERPRINT" > "$SHA256_OUT"

chmod 0600 "$PRIV_KEY" "$B64_PRIV" "$SHA256_OUT"
chmod 0644 "$DER_CERT" "$PEM_CERT"

rm -f "$EXTFILE"

cat <<EOF
Key files:
  $PRIV_KEY   (encrypted PEM)
  $DER_CERT   (DER cert)
  $PEM_CERT   (PEM cert)
  $B64_PRIV   (base64 priv)
  $SHA256_OUT (sha256 fp)
Fingerprint: $FINGERPRINT
GitHub secrets: COSIGN_PRIVATE_KEY, MIOS_MOK_KEY_B64 (= $B64_PRIV), MIOS_MOK_KEY_PASSWORD
Commit DER:    cp $DER_CERT etc/pki/mios/mok.der && git add etc/pki/mios/mok.der
Never commit:  /etc/pki/mios/mok.priv
EOF
