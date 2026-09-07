//! Independent Rust implementation of the frozen SAE-R1 canonical authority encoding.
//!
//! This crate deliberately has no dependencies on Python or third-party Rust crates.
//! Python and Rust share only the frozen encoding specification and test vectors.

use std::collections::BTreeMap;
use std::fmt;

const PREFIX: &[u8] = b"SERGEANT-AUTHORITY-V1\0";

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct IdentityError(pub String);

impl fmt::Display for IdentityError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result { write!(f, "{}", self.0) }
}

impl std::error::Error for IdentityError {}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum AuthorityValue {
    String(String),
    Boolean(bool),
    Integer(i64),
    List(Vec<AuthorityValue>),
    Object(BTreeMap<String, AuthorityValue>),
    Bytes(Vec<u8>),
    Null,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AuthorityObject {
    pub kind: String,
    pub fields: BTreeMap<String, AuthorityValue>,
}

impl AuthorityObject {
    pub fn new(kind: impl Into<String>, fields: BTreeMap<String, AuthorityValue>) -> Result<Self, IdentityError> {
        let kind = kind.into();
        validate_text(&kind, "authority object kind")?;
        for name in fields.keys() { validate_text(name, "authority field name")?; }
        Ok(Self { kind, fields })
    }
}

fn validate_text(value: &str, field: &str) -> Result<(), IdentityError> {
    if value.is_empty() || value.trim() != value {
        return Err(IdentityError(format!("{field} must be canonical and non-empty")));
    }
    Ok(())
}

fn put_u32(out: &mut Vec<u8>, value: usize) -> Result<(), IdentityError> {
    let value = u32::try_from(value).map_err(|_| IdentityError("canonical value exceeds u32 length bound".into()))?;
    out.extend_from_slice(&value.to_be_bytes());
    Ok(())
}

fn put_blob(out: &mut Vec<u8>, value: &[u8]) -> Result<(), IdentityError> {
    put_u32(out, value.len())?;
    out.extend_from_slice(value);
    Ok(())
}

fn encode_fields(out: &mut Vec<u8>, fields: &BTreeMap<String, AuthorityValue>) -> Result<(), IdentityError> {
    put_u32(out, fields.len())?;
    for (name, value) in fields {
        validate_text(name, "authority field name")?;
        put_blob(out, name.as_bytes())?;
        encode_value(out, value)?;
    }
    Ok(())
}

fn encode_value(out: &mut Vec<u8>, value: &AuthorityValue) -> Result<(), IdentityError> {
    match value {
        AuthorityValue::String(text) => {
            validate_text(text, "authority string")?;
            out.push(b's');
            put_blob(out, text.as_bytes())?;
        }
        AuthorityValue::Boolean(flag) => {
            out.push(b'b');
            out.push(if *flag { 1 } else { 0 });
        }
        AuthorityValue::Integer(number) => {
            out.push(b'i');
            out.extend_from_slice(&number.to_be_bytes());
        }
        AuthorityValue::List(values) => {
            out.push(b'l');
            put_u32(out, values.len())?;
            for item in values { encode_value(out, item)?; }
        }
        AuthorityValue::Object(fields) => {
            out.push(b'o');
            encode_fields(out, fields)?;
        }
        AuthorityValue::Bytes(bytes) => {
            out.push(b'x');
            put_blob(out, bytes)?;
        }
        AuthorityValue::Null => out.push(b'n'),
    }
    Ok(())
}

pub fn canonical_authority_bytes(value: &AuthorityObject) -> Result<Vec<u8>, IdentityError> {
    validate_text(&value.kind, "authority object kind")?;
    let mut out = Vec::new();
    out.extend_from_slice(PREFIX);
    put_blob(&mut out, value.kind.as_bytes())?;
    encode_fields(&mut out, &value.fields)?;
    Ok(out)
}

pub fn authority_id(value: &AuthorityObject) -> Result<String, IdentityError> {
    let bytes = canonical_authority_bytes(value)?;
    Ok(hex_lower(&sha256(&bytes)))
}

pub fn require_authority_id(value: &str) -> Result<&str, IdentityError> {
    if value.len() != 64 || !value.bytes().all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b)) {
        return Err(IdentityError("authority id must be a full lowercase 64-hex SHA-256 digest".into()));
    }
    Ok(value)
}

pub fn frozen_vector_object(family: &str) -> Result<AuthorityObject, IdentityError> {
    validate_text(family, "vector family")?;
    let mut scope = BTreeMap::new();
    scope.insert("a".into(), AuthorityValue::String("x".into()));
    scope.insert("z".into(), AuthorityValue::Integer(2));
    let mut fields = BTreeMap::new();
    fields.insert("active".into(), AuthorityValue::Boolean(true));
    fields.insert("count".into(), AuthorityValue::Integer(1));
    fields.insert("domain".into(), AuthorityValue::String(format!("{family}.v1")));
    fields.insert("generation".into(), AuthorityValue::String("g1".into()));
    fields.insert("refs".into(), AuthorityValue::List(vec![AuthorityValue::String("a".into()), AuthorityValue::String("b".into())]));
    fields.insert("scope".into(), AuthorityValue::Object(scope));
    AuthorityObject::new(family, fields)
}

fn hex_lower(bytes: &[u8]) -> String {
    const HEX: &[u8; 16] = b"0123456789abcdef";
    let mut out = String::with_capacity(bytes.len() * 2);
    for byte in bytes {
        out.push(HEX[(byte >> 4) as usize] as char);
        out.push(HEX[(byte & 0x0f) as usize] as char);
    }
    out
}

// FIPS 180-4 SHA-256, implemented locally so Rust identity does not depend on
// the Python implementation or a shared hashing library beyond the algorithm.
fn sha256(input: &[u8]) -> [u8; 32] {
    const K: [u32; 64] = [
        0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
        0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
        0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
        0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
        0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
        0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
        0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
        0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2,
    ];
    let mut h: [u32; 8] = [0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19];
    let bit_len = (input.len() as u64).wrapping_mul(8);
    let mut data = input.to_vec();
    data.push(0x80);
    while data.len() % 64 != 56 { data.push(0); }
    data.extend_from_slice(&bit_len.to_be_bytes());

    for chunk in data.chunks_exact(64) {
        let mut w = [0u32; 64];
        for (index, bytes) in chunk.chunks_exact(4).enumerate().take(16) {
            w[index] = u32::from_be_bytes([bytes[0], bytes[1], bytes[2], bytes[3]]);
        }
        for i in 16..64 {
            let s0 = w[i-15].rotate_right(7) ^ w[i-15].rotate_right(18) ^ (w[i-15] >> 3);
            let s1 = w[i-2].rotate_right(17) ^ w[i-2].rotate_right(19) ^ (w[i-2] >> 10);
            w[i] = w[i-16].wrapping_add(s0).wrapping_add(w[i-7]).wrapping_add(s1);
        }
        let (mut a, mut b, mut c, mut d, mut e, mut f, mut g, mut hh) = (h[0],h[1],h[2],h[3],h[4],h[5],h[6],h[7]);
        for i in 0..64 {
            let s1 = e.rotate_right(6) ^ e.rotate_right(11) ^ e.rotate_right(25);
            let ch = (e & f) ^ ((!e) & g);
            let t1 = hh.wrapping_add(s1).wrapping_add(ch).wrapping_add(K[i]).wrapping_add(w[i]);
            let s0 = a.rotate_right(2) ^ a.rotate_right(13) ^ a.rotate_right(22);
            let maj = (a & b) ^ (a & c) ^ (b & c);
            let t2 = s0.wrapping_add(maj);
            hh = g; g = f; f = e; e = d.wrapping_add(t1); d = c; c = b; b = a; a = t1.wrapping_add(t2);
        }
        h[0]=h[0].wrapping_add(a); h[1]=h[1].wrapping_add(b); h[2]=h[2].wrapping_add(c); h[3]=h[3].wrapping_add(d);
        h[4]=h[4].wrapping_add(e); h[5]=h[5].wrapping_add(f); h[6]=h[6].wrapping_add(g); h[7]=h[7].wrapping_add(hh);
    }
    let mut out = [0u8; 32];
    for (index, word) in h.iter().enumerate() { out[index*4..index*4+4].copy_from_slice(&word.to_be_bytes()); }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn sha256_known_vector_is_correct() {
        assert_eq!(hex_lower(&sha256(b"abc")), "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad");
    }

    #[test]
    fn frozen_python_rust_vectors_match() {
        let text = include_str!("../../../spec/sae-r1-canonical-vectors.txt");
        let mut seen = 0usize;
        for line in text.lines().filter(|line| !line.is_empty() && !line.starts_with('#')) {
            let (family, expected) = line.split_once('\t').expect("vector line");
            let object = frozen_vector_object(family).expect("canonical vector object");
            assert_eq!(authority_id(&object).expect("authority id"), expected, "family {family}");
            seen += 1;
        }
        assert_eq!(seen, 8);
    }

    #[test]
    fn list_order_and_type_identity_are_material() {
        let mut a = BTreeMap::new();
        a.insert("v".into(), AuthorityValue::List(vec![AuthorityValue::String("a".into()), AuthorityValue::String("b".into())]));
        let mut b = BTreeMap::new();
        b.insert("v".into(), AuthorityValue::List(vec![AuthorityValue::String("b".into()), AuthorityValue::String("a".into())]));
        assert_ne!(authority_id(&AuthorityObject::new("x", a).unwrap()).unwrap(), authority_id(&AuthorityObject::new("x", b).unwrap()).unwrap());
        let mut int_fields = BTreeMap::new(); int_fields.insert("v".into(), AuthorityValue::Integer(1));
        let mut bool_fields = BTreeMap::new(); bool_fields.insert("v".into(), AuthorityValue::Boolean(true));
        assert_ne!(authority_id(&AuthorityObject::new("x", int_fields).unwrap()).unwrap(), authority_id(&AuthorityObject::new("x", bool_fields).unwrap()).unwrap());
    }

    #[test]
    fn truncated_or_uppercase_authority_ids_fail() {
        let full = "a".repeat(64);
        assert!(require_authority_id(&full).is_ok());
        assert!(require_authority_id(&full[..16]).is_err());
        assert!(require_authority_id(&"A".repeat(64)).is_err());
    }
}
