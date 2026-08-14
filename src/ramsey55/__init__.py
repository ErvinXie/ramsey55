"""Trusted, dependency-free primitives for Ramsey(5,5) certificates."""

from .graph import Graph
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
    "ExtensionBranch",
    "ExtensionCertificate",
    "ExtensionLeaf",
    "ExtensionMultiplicityCertificate",
    "ExtensionMultiplicityCounterexample",
    "ExtensionMultiplicityLeaf",
    "attachment_violations",
    "generate_extension_certificate",
    "generate_extension_multiplicity_certificate",
    "verify_extension_certificate",
    "verify_extension_multiplicity_certificate",
]
