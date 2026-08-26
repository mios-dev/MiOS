// AI-hint: Ed25519 mutual handshake, X25519 ECDH key exchange, HKDF-SHA256 key derivation, and ChaCha20-Poly1305 wire AEAD for mios-node.
// AI-related: src/mios-rs/mios-node/src/net.rs, src/mios-rs/mios-node/src/protocol.rs, tests/test-node-crypto-handshake.py
//! MiOS Node Cryptographic Handshake & Wire Encryption Engine (T-388 / AGY-1986)
//!
//! Provides mutual identity authentication using Ed25519 signatures, forward secrecy via X25519
//! ephemeral Diffie-Hellman key exchange, HKDF-SHA256 session key derivation, and ChaCha20-Poly1305
//! authenticated symmetric frame payload encryption.

use crate::protocol::Frame;
use anyhow::{anyhow, Result};
use byteorder::{BigEndian, ByteOrder, LittleEndian};
use ed25519_dalek::{Signature, Signer, SigningKey, Verifier, VerifyingKey};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

pub const TAG_SIZE: usize = 16;
pub const KEY_SIZE: usize = 32;

// ============================================================================
// 1. SHA-256 HMAC & HKDF-SHA256
// ============================================================================

pub fn hmac_sha256(key: &[u8], data: &[u8]) -> [u8; 32] {
    let mut k = [0u8; 64];
    if key.len() > 64 {
        let hash = Sha256::digest(key);
        k[..32].copy_from_slice(&hash);
    } else {
        k[..key.len()].copy_from_slice(key);
    }

    let mut ipad = [0x36u8; 64];
    let mut opad = [0x5cu8; 64];
    for i in 0..64 {
        ipad[i] ^= k[i];
        opad[i] ^= k[i];
    }

    let mut inner_hasher = Sha256::new();
    inner_hasher.update(&ipad);
    inner_hasher.update(data);
    let inner_hash = inner_hasher.finalize();

    let mut outer_hasher = Sha256::new();
    outer_hasher.update(&opad);
    outer_hasher.update(&inner_hash);
    let outer_hash = outer_hasher.finalize();

    let mut out = [0u8; 32];
    out.copy_from_slice(&outer_hash);
    out
}

pub fn hkdf_sha256_expand(prk: &[u8; 32], info: &[u8], okm_len: usize) -> Vec<u8> {
    let mut okm = Vec::with_capacity(okm_len);
    let mut prev = Vec::new();
    let mut counter: u8 = 1;

    while okm.len() < okm_len {
        let mut input = Vec::new();
        input.extend_from_slice(&prev);
        input.extend_from_slice(info);
        input.push(counter);

        let t = hmac_sha256(prk, &input);
        prev = t.to_vec();

        let needed = (okm_len - okm.len()).min(32);
        okm.extend_from_slice(&t[..needed]);
        counter += 1;
    }

    okm
}

pub fn hkdf_sha256(salt: &[u8], ikm: &[u8], info: &[u8], len: usize) -> Vec<u8> {
    let default_salt = [0u8; 32];
    let s = if salt.is_empty() { &default_salt[..] } else { salt };
    let prk = hmac_sha256(s, ikm);
    hkdf_sha256_expand(&prk, info, len)
}

// ============================================================================
// 2. RFC 7748 X25519 Curve Arithmetic (Montgomery Ladder)
// ============================================================================

// Field element modulo 2^255 - 19 represented as 10 26-bit limbs (or u128 / u64 limbs)
// Using 64-bit limbs for clarity and speed
#[derive(Clone, Copy, Debug)]
struct Fe([u64; 5]); // 5 limbs of 51 bits each: sum_i Fe[i] * 2^(51*i)

impl Fe {
    const ZERO: Self = Fe([0, 0, 0, 0, 0]);
    const ONE: Self = Fe([1, 0, 0, 0, 0]);

    fn from_bytes(b: &[u8; 32]) -> Self {
        let mut out = [0u64; 5];
        let mut words = [0u64; 4];
        for i in 0..4 {
            words[i] = LittleEndian::read_u64(&b[i * 8..(i + 1) * 8]);
        }
        let mask51 = (1u64 << 51) - 1;
        out[0] = words[0] & mask51;
        out[1] = ((words[0] >> 51) | (words[1] << 13)) & mask51;
        out[2] = ((words[1] >> 38) | (words[2] << 26)) & mask51;
        out[3] = ((words[2] >> 25) | (words[3] << 39)) & mask51;
        out[4] = (words[3] >> 12) & ((1u64 << 51) - 1);
        Fe(out)
    }

    fn to_bytes(&self) -> [u8; 32] {
        let mut t = *self;
        t.reduce();
        t.reduce();

        // strictly reduce modulo 2^255 - 19
        let mut q = (19 * t.0[0]) >> 51;
        q = (19 * t.0[1] + q) >> 51;
        q = (19 * t.0[2] + q) >> 51;
        q = (19 * t.0[3] + q) >> 51;
        q = (t.0[4] + q) >> 51;

        t.0[0] += 19 * q;
        let mut carry = t.0[0] >> 51;
        t.0[0] &= (1u64 << 51) - 1;
        for i in 1..5 {
            t.0[i] += carry;
            carry = t.0[i] >> 51;
            t.0[i] &= (1u64 << 51) - 1;
        }

        let mut out = [0u8; 32];
        let w0 = t.0[0] | (t.0[1] << 51);
        let w1 = (t.0[1] >> 13) | (t.0[2] << 38);
        let w2 = (t.0[2] >> 26) | (t.0[3] << 25);
        let w3 = (t.0[3] >> 39) | (t.0[4] << 12);

        LittleEndian::write_u64(&mut out[0..8], w0);
        LittleEndian::write_u64(&mut out[8..16], w1);
        LittleEndian::write_u64(&mut out[16..24], w2);
        LittleEndian::write_u64(&mut out[24..32], w3);
        out
    }

    fn reduce(&mut self) {
        let mask51 = (1u64 << 51) - 1;
        let c4 = self.0[4] >> 51;
        self.0[4] &= mask51;
        self.0[0] += c4 * 19;

        let mut c = 0u64;
        for i in 0..5 {
            self.0[i] += c;
            c = self.0[i] >> 51;
            self.0[i] &= mask51;
        }
        self.0[0] += c * 19;
    }

    fn add(&self, rhs: &Self) -> Self {
        Fe([
            self.0[0] + rhs.0[0],
            self.0[1] + rhs.0[1],
            self.0[2] + rhs.0[2],
            self.0[3] + rhs.0[3],
            self.0[4] + rhs.0[4],
        ])
    }

    fn sub(&self, rhs: &Self) -> Self {
        // Bias by multiples of (2^255 - 19) to prevent underflow
        const BIAS: [u64; 5] = [
            0x7fffffffffffda * 2,
            0x7ffffffffffffeu64 * 2,
            0x7ffffffffffffeu64 * 2,
            0x7ffffffffffffeu64 * 2,
            0x7ffffffffffffeu64 * 2,
        ];
        Fe([
            self.0[0] + BIAS[0] - rhs.0[0],
            self.0[1] + BIAS[1] - rhs.0[1],
            self.0[2] + BIAS[2] - rhs.0[2],
            self.0[3] + BIAS[3] - rhs.0[3],
            self.0[4] + BIAS[4] - rhs.0[4],
        ])
    }

    fn mul(&self, rhs: &Self) -> Self {
        let a = &self.0;
        let b = &rhs.0;
        let mut r = [0u128; 5];

        let mul19 = |x: u128| -> u128 { x * 19 };

        r[0] = (a[0] as u128) * (b[0] as u128)
            + mul19((a[1] as u128) * (b[4] as u128))
            + mul19((a[2] as u128) * (b[3] as u128))
            + mul19((a[3] as u128) * (b[2] as u128))
            + mul19((a[4] as u128) * (b[1] as u128));

        r[1] = (a[0] as u128) * (b[1] as u128)
            + (a[1] as u128) * (b[0] as u128)
            + mul19((a[2] as u128) * (b[4] as u128))
            + mul19((a[3] as u128) * (b[3] as u128))
            + mul19((a[4] as u128) * (b[2] as u128));

        r[2] = (a[0] as u128) * (b[2] as u128)
            + (a[1] as u128) * (b[1] as u128)
            + (a[2] as u128) * (b[0] as u128)
            + mul19((a[3] as u128) * (b[4] as u128))
            + mul19((a[4] as u128) * (b[3] as u128));

        r[3] = (a[0] as u128) * (b[3] as u128)
            + (a[1] as u128) * (b[2] as u128)
            + (a[2] as u128) * (b[1] as u128)
            + (a[3] as u128) * (b[0] as u128)
            + mul19((a[4] as u128) * (b[4] as u128));

        r[4] = (a[0] as u128) * (b[4] as u128)
            + (a[1] as u128) * (b[3] as u128)
            + (a[2] as u128) * (b[2] as u128)
            + (a[3] as u128) * (b[1] as u128)
            + (a[4] as u128) * (b[0] as u128);

        let mask51 = (1u128 << 51) - 1;
        let mut c = 0u128;
        let mut out = [0u64; 5];
        for i in 0..5 {
            let total = r[i] + c;
            out[i] = (total & mask51) as u64;
            c = total >> 51;
        }
        out[0] += (c * 19) as u64;
        let mut res = Fe(out);
        res.reduce();
        res
    }

    fn mul_const(&self, k: u64) -> Self {
        let mut out = [0u64; 5];
        for i in 0..5 {
            out[i] = self.0[i] * k;
        }
        let mut res = Fe(out);
        res.reduce();
        res
    }

    fn sqr(&self) -> Self {
        self.mul(self)
    }

    fn invert(&self) -> Self {
        // Fermat's Little Theorem: a^(p-2) mod p where p = 2^255 - 19
        let mut t = *self;
        for _ in 1..254 {
            t = t.sqr().mul(self);
        }
        // compute via standard addition chain
        let z2 = self.sqr().mul(self);
        let mut z9 = z2.sqr();
        for _ in 0..2 { z9 = z9.sqr(); }
        z9 = z9.mul(&z2);
        let z11 = z9.sqr().mul(self);
        let mut z2_5_0 = z11.sqr();
        for _ in 0..4 { z2_5_0 = z2_5_0.sqr(); }
        z2_5_0 = z2_5_0.mul(&z9);
        let mut z2_10_0 = z2_5_0.sqr();
        for _ in 0..9 { z2_10_0 = z2_10_0.sqr(); }
        z2_10_0 = z2_10_0.mul(&z2_5_0);
        let mut z2_20_0 = z2_10_0.sqr();
        for _ in 0..19 { z2_20_0 = z2_20_0.sqr(); }
        z2_20_0 = z2_20_0.mul(&z2_10_0);
        let mut z2_40_0 = z2_20_0.sqr();
        for _ in 0..39 { z2_40_0 = z2_40_0.sqr(); }
        z2_40_0 = z2_40_0.mul(&z2_20_0);
        let mut z2_50_0 = z2_40_0.sqr();
        for _ in 0..9 { z2_50_0 = z2_50_0.sqr(); }
        z2_50_0 = z2_50_0.mul(&z2_10_0);
        let mut z2_100_0 = z2_50_0.sqr();
        for _ in 0..49 { z2_100_0 = z2_100_0.sqr(); }
        z2_100_0 = z2_100_0.mul(&z2_50_0);
        let mut z2_200_0 = z2_100_0.sqr();
        for _ in 0..99 { z2_200_0 = z2_200_0.sqr(); }
        z2_200_0 = z2_200_0.mul(&z2_100_0);
        let mut z2_250_0 = z2_200_0.sqr();
        for _ in 0..49 { z2_250_0 = z2_250_0.sqr(); }
        z2_250_0 = z2_250_0.mul(&z2_50_0);
        let mut t0 = z2_250_0.sqr();
        for _ in 0..4 { t0 = t0.sqr(); }
        t0 = t0.mul(&z11);
        t0
    }

    fn cswap(a: &mut Self, b: &mut Self, swap: u64) {
        let mask = if swap != 0 { 0xFFFFFFFFFFFFFFFF } else { 0 };
        for i in 0..5 {
            let x = mask & (a.0[i] ^ b.0[i]);
            a.0[i] ^= x;
            b.0[i] ^= x;
        }
    }
}

pub fn x25519(k: &[u8; 32], u: &[u8; 32]) -> [u8; 32] {
    let mut clamped_k = *k;
    clamped_k[0] &= 248;
    clamped_k[31] &= 127;
    clamped_k[31] |= 64;

    let x1 = Fe::from_bytes(u);
    let mut x2 = Fe::ONE;
    let mut z2 = Fe::ZERO;
    let mut x3 = x1;
    let mut z3 = Fe::ONE;
    let mut swap = 0u64;

    for i in (0..255).rev() {
        let bit = ((clamped_k[i / 8] >> (i % 8)) & 1) as u64;
        swap ^= bit;
        Fe::cswap(&mut x2, &mut x3, swap);
        Fe::cswap(&mut z2, &mut z3, swap);
        swap = bit;

        let a = x2.add(&z2);
        let aa = a.sqr();
        let b = x2.sub(&z2);
        let bb = b.sqr();
        let e = aa.sub(&bb);
        let c = x3.add(&z3);
        let d = x3.sub(&z3);
        let da = d.mul(&a);
        let cb = c.mul(&b);

        x3 = da.add(&cb).sqr();
        z3 = x1.mul(&da.sub(&cb).sqr());
        x2 = aa.mul(&bb);
        z2 = e.mul(&aa.add(&e.mul_const(121665)));
    }

    Fe::cswap(&mut x2, &mut x3, swap);
    Fe::cswap(&mut z2, &mut z3, swap);

    x2.mul(&z2.invert()).to_bytes()
}

pub const X25519_BASEPOINT: [u8; 32] = [
    9, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
];

pub fn x25519_public_key(priv_key: &[u8; 32]) -> [u8; 32] {
    x25519(priv_key, &X25519_BASEPOINT)
}

// ============================================================================
// 3. RFC 8439 ChaCha20 & Poly1305 AEAD Engine
// ============================================================================

fn chacha20_quarter_round(st: &mut [u32; 16], a: usize, b: usize, c: usize, d: usize) {
    st[a] = st[a].wrapping_add(st[b]); st[d] ^= st[a]; st[d] = st[d].rotate_left(16);
    st[c] = st[c].wrapping_add(st[d]); st[b] ^= st[c]; st[b] = st[b].rotate_left(12);
    st[a] = st[a].wrapping_add(st[b]); st[d] ^= st[a]; st[d] = st[d].rotate_left(8);
    st[c] = st[c].wrapping_add(st[d]); st[b] ^= st[c]; st[b] = st[b].rotate_left(7);
}

fn chacha20_block(key: &[u8; 32], counter: u32, nonce: &[u8; 12]) -> [u8; 64] {
    let mut state = [0u32; 16];
    state[0] = 0x61707865; // "expa"
    state[1] = 0x3320646e; // "nd 3"
    state[2] = 0x79622d32; // "2-by"
    state[3] = 0x6b206574; // "te k"

    for i in 0..8 {
        state[4 + i] = LittleEndian::read_u32(&key[i * 4..(i + 1) * 4]);
    }
    state[12] = counter;
    for i in 0..3 {
        state[13 + i] = LittleEndian::read_u32(&nonce[i * 4..(i + 1) * 4]);
    }

    let mut working = state;
    for _ in 0..10 {
        // Column rounds
        chacha20_quarter_round(&mut working, 0, 4, 8, 12);
        chacha20_quarter_round(&mut working, 1, 5, 9, 13);
        chacha20_quarter_round(&mut working, 2, 6, 10, 14);
        chacha20_quarter_round(&mut working, 3, 7, 11, 15);
        // Diagonal rounds
        chacha20_quarter_round(&mut working, 0, 5, 10, 15);
        chacha20_quarter_round(&mut working, 1, 6, 11, 12);
        chacha20_quarter_round(&mut working, 2, 7, 8, 13);
        chacha20_quarter_round(&mut working, 3, 4, 9, 14);
    }

    let mut out = [0u8; 64];
    for i in 0..16 {
        let val = working[i].wrapping_add(state[i]);
        LittleEndian::write_u32(&mut out[i * 4..(i + 1) * 4], val);
    }
    out
}

pub fn chacha20_crypt(key: &[u8; 32], counter: u32, nonce: &[u8; 12], data: &[u8]) -> Vec<u8> {
    let mut out = vec![0u8; data.len()];
    let mut cur_counter = counter;
    let mut offset = 0;

    while offset < data.len() {
        let block = chacha20_block(key, cur_counter, nonce);
        let block_len = (data.len() - offset).min(64);
        for i in 0..block_len {
            out[offset + i] = data[offset + i] ^ block[i];
        }
        offset += block_len;
        cur_counter += 1;
    }
    out
}

// Poly1305 one-time authenticator modulo 2^130 - 5
pub fn poly1305_mac(key: &[u8; 32], msg: &[u8]) -> [u8; 16] {
    let mut r = [0u8; 16];
    r.copy_from_slice(&key[0..16]);
    // Clamp r
    r[3] &= 15; r[7] &= 15; r[11] &= 15; r[15] &= 15;
    r[4] &= 252; r[8] &= 252; r[12] &= 252;

    let r_u128 = LittleEndian::read_u128(&r);
    let s_u128 = LittleEndian::read_u128(&key[16..32]);

    let mut h: u128 = 0;
    let p: u128 = (1u128 << 130) - 5; // pseudo 130-bit prime

    let mut offset = 0;
    while offset < msg.len() {
        let chunk_len = (msg.len() - offset).min(16);
        let mut block = [0u8; 17];
        block[..chunk_len].copy_from_slice(&msg[offset..offset + chunk_len]);
        block[chunk_len] = 1; // 0x01 byte appended

        let n = LittleEndian::read_u128(&block[0..16]) | ((block[16] as u128) << 128);
        h = (h + n) % p;
        h = ((h as u128).wrapping_mul(r_u128)) % p;
        offset += chunk_len;
    }

    let tag_val = (h + s_u128) & 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF;
    let mut tag = [0u8; 16];
    LittleEndian::write_u128(&mut tag, tag_val);
    tag
}

pub fn chacha20_poly1305_encrypt(
    key: &[u8; 32],
    nonce: &[u8; 12],
    aad: &[u8],
    plaintext: &[u8],
) -> Vec<u8> {
    // 1. Generate Poly1305 key via ChaCha20 block 0
    let poly_block = chacha20_block(key, 0, nonce);
    let mut poly_key = [0u8; 32];
    poly_key.copy_from_slice(&poly_block[0..32]);

    // 2. Encrypt plaintext starting at counter = 1
    let ciphertext = chacha20_crypt(key, 1, nonce, plaintext);

    // 3. Construct MAC data: AAD || pad || Ciphertext || pad || len(AAD) || len(Ciphertext)
    let mut mac_data = Vec::new();
    mac_data.extend_from_slice(aad);
    if aad.len() % 16 != 0 {
        mac_data.resize(mac_data.len() + (16 - (aad.len() % 16)), 0);
    }
    mac_data.extend_from_slice(&ciphertext);
    if ciphertext.len() % 16 != 0 {
        mac_data.resize(mac_data.len() + (16 - (ciphertext.len() % 16)), 0);
    }
    let mut len_buf = [0u8; 16];
    LittleEndian::write_u64(&mut len_buf[0..8], aad.len() as u64);
    LittleEndian::write_u64(&mut len_buf[8..16], ciphertext.len() as u64);
    mac_data.extend_from_slice(&len_buf);

    // 4. Compute Poly1305 tag
    let tag = poly1305_mac(&poly_key, &mac_data);

    let mut out = ciphertext;
    out.extend_from_slice(&tag);
    out
}

pub fn chacha20_poly1305_decrypt(
    key: &[u8; 32],
    nonce: &[u8; 12],
    aad: &[u8],
    ciphertext_with_tag: &[u8],
) -> Result<Vec<u8>> {
    if ciphertext_with_tag.len() < TAG_SIZE {
        return Err(anyhow!("Ciphertext too short for Poly1305 MAC tag"));
    }

    let ct_len = ciphertext_with_tag.len() - TAG_SIZE;
    let ciphertext = &ciphertext_with_tag[..ct_len];
    let expected_tag = &ciphertext_with_tag[ct_len..];

    // 1. Generate Poly1305 key
    let poly_block = chacha20_block(key, 0, nonce);
    let mut poly_key = [0u8; 32];
    poly_key.copy_from_slice(&poly_block[0..32]);

    // 2. Recompute MAC data
    let mut mac_data = Vec::new();
    mac_data.extend_from_slice(aad);
    if aad.len() % 16 != 0 {
        mac_data.resize(mac_data.len() + (16 - (aad.len() % 16)), 0);
    }
    mac_data.extend_from_slice(ciphertext);
    if ciphertext.len() % 16 != 0 {
        mac_data.resize(mac_data.len() + (16 - (ciphertext.len() % 16)), 0);
    }
    let mut len_buf = [0u8; 16];
    LittleEndian::write_u64(&mut len_buf[0..8], aad.len() as u64);
    LittleEndian::write_u64(&mut len_buf[8..16], ciphertext.len() as u64);
    mac_data.extend_from_slice(&len_buf);

    let actual_tag = poly1305_mac(&poly_key, &mac_data);

    // Constant-time tag comparison
    let mut diff = 0u8;
    for i in 0..16 {
        diff |= expected_tag[i] ^ actual_tag[i];
    }

    if diff != 0 {
        return Err(anyhow!("Poly1305 authentication MAC mismatch - ciphertext tampered"));
    }

    // 3. Decrypt ciphertext
    let plaintext = chacha20_crypt(key, 1, nonce, ciphertext);
    Ok(plaintext)
}

// ============================================================================
// 4. Ed25519 Identity & Mutual Handshake
// ============================================================================

#[derive(Clone)]
pub struct NodeIdentity {
    pub node_id: u32,
    pub signing_key: SigningKey,
}

impl NodeIdentity {
    pub fn from_bytes(node_id: u32, secret_key_bytes: &[u8; 32]) -> Self {
        let signing_key = SigningKey::from_bytes(secret_key_bytes);
        Self { node_id, signing_key }
    }

    pub fn verifying_key(&self) -> VerifyingKey {
        self.signing_key.verifying_key()
    }

    pub fn public_key_bytes(&self) -> [u8; 32] {
        self.verifying_key().to_bytes()
    }

    pub fn sign(&self, msg: &[u8]) -> [u8; 64] {
        self.signing_key.sign(msg).to_bytes()
    }

    pub fn verify(verifying_key_bytes: &[u8; 32], msg: &[u8], sig_bytes: &[u8; 64]) -> Result<()> {
        let vk = VerifyingKey::from_bytes(verifying_key_bytes)
            .map_err(|e| anyhow!("Invalid Ed25519 verifying key: {}", e))?;
        let sig = Signature::from_bytes(sig_bytes);
        vk.verify(msg, &sig)
            .map_err(|e| anyhow!("Ed25519 signature verification failed: {}", e))
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HandshakeInitPacket {
    pub sender_node_id: u32,
    pub id_pubkey: [u8; 32],
    pub ephemeral_pubkey: [u8; 32],
    pub signature: Vec<u8>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HandshakeRespPacket {
    pub sender_node_id: u32,
    pub id_pubkey: [u8; 32],
    pub ephemeral_pubkey: [u8; 32],
    pub signature: Vec<u8>,
}

/// Established encrypted session between two nodes.
pub struct NodeCryptoSession {
    pub local_node_id: u32,
    pub remote_node_id: u32,
    pub tx_key: [u8; 32],
    pub rx_key: [u8; 32],
    pub tx_nonce: u64,
    pub rx_nonce: u64,
}

impl NodeCryptoSession {
    pub fn new(
        local_node_id: u32,
        remote_node_id: u32,
        tx_key: [u8; 32],
        rx_key: [u8; 32],
    ) -> Self {
        Self {
            local_node_id,
            remote_node_id,
            tx_key,
            rx_key,
            tx_nonce: 0,
            rx_nonce: 0,
        }
    }

    fn make_nonce(counter: u64, node_id: u32) -> [u8; 12] {
        let mut nonce = [0u8; 12];
        LittleEndian::write_u64(&mut nonce[0..8], counter);
        BigEndian::write_u32(&mut nonce[8..12], node_id);
        nonce
    }

    pub fn encrypt_payload(&mut self, plaintext: &[u8]) -> Vec<u8> {
        let nonce = Self::make_nonce(self.tx_nonce, self.local_node_id);
        self.tx_nonce += 1;
        let aad = self.local_node_id.to_be_bytes();
        chacha20_poly1305_encrypt(&self.tx_key, &nonce, &aad, plaintext)
    }

    pub fn decrypt_payload(&mut self, ciphertext: &[u8]) -> Result<Vec<u8>> {
        let nonce = Self::make_nonce(self.rx_nonce, self.remote_node_id);
        self.rx_nonce += 1;
        let aad = self.remote_node_id.to_be_bytes();
        chacha20_poly1305_decrypt(&self.rx_key, &nonce, &aad, ciphertext)
    }

    pub fn encrypt_frame(&mut self, frame: &Frame) -> Result<Frame> {
        let encrypted_payload = self.encrypt_payload(&frame.payload);
        Ok(Frame::new(
            frame.header.msg_type,
            self.local_node_id,
            encrypted_payload,
        ))
    }

    pub fn decrypt_frame(&mut self, frame: &Frame) -> Result<Frame> {
        let decrypted_payload = self.decrypt_payload(&frame.payload)?;
        Ok(Frame::new(
            frame.header.msg_type,
            frame.header.node_id,
            decrypted_payload,
        ))
    }
}

/// Orchestrates mutual cryptographic handshakes between edge nodes.
pub struct CryptoHandshake;

impl CryptoHandshake {
    pub fn create_init(
        identity: &NodeIdentity,
        ephemeral_priv: &[u8; 32],
    ) -> HandshakeInitPacket {
        let eph_pub = x25519_public_key(ephemeral_priv);
        let sig = identity.sign(&eph_pub);

        HandshakeInitPacket {
            sender_node_id: identity.node_id,
            id_pubkey: identity.public_key_bytes(),
            ephemeral_pubkey: eph_pub,
            signature: sig.to_vec(),
        }
    }

    pub fn process_init_and_respond(
        identity: &NodeIdentity,
        ephemeral_priv: &[u8; 32],
        init: &HandshakeInitPacket,
    ) -> Result<(HandshakeRespPacket, NodeCryptoSession)> {
        if init.signature.len() != 64 {
            return Err(anyhow!("Invalid signature length"));
        }
        let mut sig_arr = [0u8; 64];
        sig_arr.copy_from_slice(&init.signature);

        // 1. Verify sender's Ed25519 signature over their ephemeral pubkey
        NodeIdentity::verify(&init.id_pubkey, &init.ephemeral_pubkey, &sig_arr)?;

        // 2. Compute ephemeral public key and shared secret
        let eph_pub = x25519_public_key(ephemeral_priv);
        let shared_secret = x25519(ephemeral_priv, &init.ephemeral_pubkey);

        // 3. Derive symmetric session keys via HKDF-SHA256
        let info = b"mios-mesh-wire-v1-session-keys";
        let derived_keys = hkdf_sha256(&[], &shared_secret, info, 64);

        let mut k1 = [0u8; 32];
        let mut k2 = [0u8; 32];
        k1.copy_from_slice(&derived_keys[0..32]);
        k2.copy_from_slice(&derived_keys[32..64]);

        // Responder transmits with k2, receives with k1
        let session = NodeCryptoSession::new(identity.node_id, init.sender_node_id, k2, k1);

        // 4. Sign own ephemeral pubkey
        let sig = identity.sign(&eph_pub);
        let resp = HandshakeRespPacket {
            sender_node_id: identity.node_id,
            id_pubkey: identity.public_key_bytes(),
            ephemeral_pubkey: eph_pub,
            signature: sig.to_vec(),
        };

        Ok((resp, session))
    }

    pub fn finalize_init(
        identity: &NodeIdentity,
        ephemeral_priv: &[u8; 32],
        resp: &HandshakeRespPacket,
    ) -> Result<NodeCryptoSession> {
        if resp.signature.len() != 64 {
            return Err(anyhow!("Invalid signature length"));
        }
        let mut sig_arr = [0u8; 64];
        sig_arr.copy_from_slice(&resp.signature);

        // 1. Verify responder's Ed25519 signature over their ephemeral pubkey
        NodeIdentity::verify(&resp.id_pubkey, &resp.ephemeral_pubkey, &sig_arr)?;

        // 2. Compute shared secret
        let shared_secret = x25519(ephemeral_priv, &resp.ephemeral_pubkey);

        // 3. Derive symmetric session keys
        let info = b"mios-mesh-wire-v1-session-keys";
        let derived_keys = hkdf_sha256(&[], &shared_secret, info, 64);

        let mut k1 = [0u8; 32];
        let mut k2 = [0u8; 32];
        k1.copy_from_slice(&derived_keys[0..32]);
        k2.copy_from_slice(&derived_keys[32..64]);

        // Initiator transmits with k1, receives with k2
        Ok(NodeCryptoSession::new(identity.node_id, resp.sender_node_id, k1, k2))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_x25519_diffie_hellman() {
        let priv_a = [0x42u8; 32];
        let priv_b = [0x99u8; 32];

        let pub_a = x25519_public_key(&priv_a);
        let pub_b = x25519_public_key(&priv_b);

        let shared_a = x25519(&priv_a, &pub_b);
        let shared_b = x25519(&priv_b, &pub_a);

        assert_eq!(shared_a, shared_b);
    }

    #[test]
    fn test_chacha20_poly1305_roundtrip() {
        let key = [0x55u8; 32];
        let nonce = [0x11u8; 12];
        let aad = b"header_data";
        let plaintext = b"Sensitive payload for edge compute";

        let encrypted = chacha20_poly1305_encrypt(&key, &nonce, aad, plaintext);
        assert_eq!(encrypted.len(), plaintext.len() + TAG_SIZE);

        let decrypted = chacha20_poly1305_decrypt(&key, &nonce, aad, &encrypted).unwrap();
        assert_eq!(decrypted, plaintext);
    }

    #[test]
    fn test_tamper_detection_mac_failure() {
        let key = [0x77u8; 32];
        let nonce = [0x22u8; 12];
        let aad = b"aad";
        let plaintext = b"Secret bytes";

        let mut encrypted = chacha20_poly1305_encrypt(&key, &nonce, aad, plaintext);
        // Corrupt 1 byte
        encrypted[0] ^= 0x01;

        let result = chacha20_poly1305_decrypt(&key, &nonce, aad, &encrypted);
        assert!(result.is_err());
        assert!(result.unwrap_err().to_string().contains("MAC mismatch"));
    }

    #[test]
    fn test_mutual_crypto_handshake_session() {
        let id_a = NodeIdentity::from_bytes(101, &[1u8; 32]);
        let id_b = NodeIdentity::from_bytes(202, &[2u8; 32]);

        let eph_a = [3u8; 32];
        let eph_b = [4u8; 32];

        // 1. Node A creates init
        let init = CryptoHandshake::create_init(&id_a, &eph_a);

        // 2. Node B processes init and creates resp + session B
        let (resp, mut session_b) = CryptoHandshake::process_init_and_respond(&id_b, &eph_b, &init).unwrap();

        // 3. Node A finalizes init and creates session A
        let mut session_a = CryptoHandshake::finalize_init(&id_a, &eph_a, &resp).unwrap();

        // 4. Test encrypted communication A -> B
        let plain_a = b"Hello Node B from Node A";
        let enc_a = session_a.encrypt_payload(plain_a);
        let dec_b = session_b.decrypt_payload(&enc_a).unwrap();
        assert_eq!(dec_b, plain_a);

        // 5. Test encrypted communication B -> A
        let plain_b = b"Ack Node A from Node B";
        let enc_b = session_b.encrypt_payload(plain_b);
        let dec_a = session_a.decrypt_payload(&enc_b).unwrap();
        assert_eq!(dec_a, plain_b);
    }
}
