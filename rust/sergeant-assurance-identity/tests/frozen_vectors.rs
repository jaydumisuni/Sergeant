use sergeant_assurance_identity::{authority_id, canonical_authority_bytes, frozen_vector_object};

fn hex_lower(bytes: &[u8]) -> String {
    const HEX: &[u8; 16] = b"0123456789abcdef";
    let mut out = String::with_capacity(bytes.len() * 2);
    for byte in bytes {
        out.push(HEX[(byte >> 4) as usize] as char);
        out.push(HEX[(byte & 0x0f) as usize] as char);
    }
    out
}

#[test]
fn every_frozen_vector_matches_exact_rust_bytes_and_digest() {
    let text = include_str!("../../../spec/sae-r1-canonical-byte-vectors.txt");
    let mut seen = 0usize;
    for line in text.lines().filter(|line| !line.is_empty() && !line.starts_with('#')) {
        let mut fields = line.split('\t');
        let family = fields.next().expect("family");
        let expected_bytes = fields.next().expect("canonical bytes");
        let expected_id = fields.next().expect("authority id");
        assert!(fields.next().is_none(), "unexpected vector columns for {family}");
        let object = frozen_vector_object(family).expect("canonical vector object");
        let actual_bytes = canonical_authority_bytes(&object).expect("canonical bytes");
        assert_eq!(hex_lower(&actual_bytes), expected_bytes, "canonical bytes for {family}");
        assert_eq!(authority_id(&object).expect("authority id"), expected_id, "authority id for {family}");
        seen += 1;
    }
    assert_eq!(seen, 8);
}
