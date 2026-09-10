use sergeant_assurance_kernel::{ADMISSIBLE, INADMISSIBLE};

fn main() {
    // The production capsule transport is added only after its contract is
    // frozen. Until then this binary exposes no permissive parsing surface.
    let _ = (ADMISSIBLE, INADMISSIBLE);
}
