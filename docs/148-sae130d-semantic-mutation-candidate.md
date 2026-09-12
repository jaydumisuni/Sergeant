# SAE-130D Semantic Mutation / Falsification Candidate

This candidate is based on SAE-130C PROVEN `4b3a59117c6ccfac5d6d6d47f795cb4333566b69` and implements the roadmap SAE-130D semantic-mutation qualification surface without changing frozen predecessor authority.

The required hostile inventory is exact: guard deletion, authority substitution, route addition, missing binding/member, recovery breakage, generation/state mutation, evidence omission, and no-op detection. Material mutants must change semantic identity; the no-op detector mutant must not. Every required family must be present and every admitted mutant must be killed. A missing family or any surviving mutant leaves qualification false.

`main_review/semantic_mutation.py` is deliberately bounded to mutation evidence and qualification. It does not issue a Sergeant verdict, activate Genesis, weaken SAE-90 falsification requirements, import Tenfold command authority, or turn mutation existence into proof. Candidate merge grants no qualified capability: `QUALIFIED_SEMANTIC_MUTATION_CAPABILITY` exists only after a separate exact-head PROVEN lifecycle closeout is independently proved, reviewed, and guarded-merged.
