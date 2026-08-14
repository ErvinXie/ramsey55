"""Trusted, dependency-free primitives for Ramsey(5,5) certificates."""

from .graph import Graph
from .order45 import (
    ORDER45_BRANCH_DEGREES,
    NormalizedOrder45Graph,
    normalize_order45_degree_branch,
    relabel_with_star_at_zero,
)
from .extension import (
    ExtensionBranch,
    ExtensionCertificate,
    ExtensionLeaf,
    ExtensionMultiplicityCertificate,
    ExtensionMultiplicityCounterexample,
    ExtensionMultiplicityLeaf,
    attachment_violations,
    generate_extension_certificate,
    generate_extension_multiplicity_certificate,
    verify_extension_certificate,
    verify_extension_multiplicity_certificate,
)

__all__ = [
    "Graph",
    "ORDER45_BRANCH_DEGREES",
    "NormalizedOrder45Graph",
    "ExtensionBranch",
    "ExtensionCertificate",
    "ExtensionLeaf",
    "ExtensionMultiplicityCertificate",
    "ExtensionMultiplicityCounterexample",
    "ExtensionMultiplicityLeaf",
    "attachment_violations",
    "generate_extension_certificate",
    "generate_extension_multiplicity_certificate",
    "normalize_order45_degree_branch",
    "relabel_with_star_at_zero",
    "verify_extension_certificate",
    "verify_extension_multiplicity_certificate",
]
