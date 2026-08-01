#!/usr/bin/bash
# AI-hint: One-shot script to generate a 2048-bit RSA MOK key with specific code-signing EKU extensions for kernel module signing, outputting to /etc/pki/mios/ for use in secure boot verification.
set -euo pipefail

KEY_DIR=/etc/pki/mios
PRIV_KEY="${KEY_DIR}/mok.priv"
DER_CERT="${KEY_DIR}/mok.der"
PEM_CERT="${KEY_DIR}/mok.pem"
B64_PRIV="${KEY_DIR}/mok.priv.b64"
SHA256_OUT="${KEY_DIR}/mok.sha256"

if [[ -f "$DER_CERT" ]]; then
    echo "ERROR: $DER_CERT already exists. MOK keys are generated once"
    echo "If you need to rotate, delete the old key files first, re-enroll with mokutil,"
    echo "And then re-run this script"
    exit 1
fi

if [[ "$(id -u)" -ne 0 ]]; then
    echo "ERROR: run as root"
    exit 1
fi

install -d -m 0700 "$KEY_DIR"

echo "'MiOS' MOK key generation"
echo "Set passphrase prompt: store in GitHub secret MIOS_MOK_KEY_PASSWORD"

EXTFILE=$(mktemp /tmp/mok-ext.XXXXXX.conf)
cat >"$EXTFILE" <<'EOF'
[req]
default_bits       = 2048
default_md         = sha256
distinguished_name = dn
x509_extensions    = v3_ca
prompt             = no

[dn]
CN = 'MiOS' Module Signing Key

[v3_ca]
basicConstraints       = CA:FALSE
keyUsage               = digitalSignature
extendedKeyUsage       = codeSigning, 1.3.6.1.5.5.7.3.3, 1.3.6.1.4.1.311.61.1.1, 1.3.6.1.4.1.311.10.3.5
subjectKeyIdentifier   = hash
authorityKeyIdentifier = keyid:always
EOF

openssl req \
    -newkey rsa:2048 \
    -nodes \
    -keyout "${PRIV_KEY}.plain" \
    -x509 \
    -outform PEM \
    -out "$PEM_CERT" \
    -days 3650 \
    -config "$EXTFILE"

openssl x509 -in "$PEM_CERT" -outform DER -out "$DER_CERT"

echo "Enter passphrase to encrypt the private key:"
openssl pkcs8 -topk8 -inform PEM -outform PEM \
    -in "${PRIV_KEY}.plain" \
    -out "$PRIV_KEY"
rm -f "${PRIV_KEY}.plain"

base64 -w0 "$PRIV_KEY" > "$B64_PRIV"

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
