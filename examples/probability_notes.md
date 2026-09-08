# Probability and Statistics — Conditional Probability

## Conditional probability

For events A and B with P(B) > 0,

P(A | B) = P(A ∩ B) / P(B).

Conditioning changes the sample space from the whole population to outcomes in B.

## Multiplication rule

P(A ∩ B) = P(A | B)P(B) = P(B | A)P(A).

## Independence

A and B are independent when P(A ∩ B) = P(A)P(B). Equivalently, when the relevant
probabilities are non-zero, P(A | B) = P(A). Independence is not the same as mutual
exclusivity: two mutually exclusive events with positive probability cannot be independent.

## Law of total probability

If B1, ..., Bn form a partition of the sample space, then

P(A) = Σ P(A | Bi)P(Bi).

## Bayes' theorem

P(Bj | A) = P(A | Bj)P(Bj) / Σ P(A | Bi)P(Bi).

The prior P(Bj) is updated using the likelihood P(A | Bj). The denominator is the
evidence or marginal probability of A. The result P(Bj | A) is the posterior.

## Example: medical screening

A condition affects 1% of a population. A test has 95% sensitivity and a 5% false-positive
rate. For a positive result:

P(condition | positive) = (0.95 × 0.01) / [(0.95 × 0.01) + (0.05 × 0.99)] ≈ 0.161.

The posterior is much lower than 95% because the condition is rare. Confusing sensitivity
with the probability of disease after a positive test is the base-rate fallacy.
