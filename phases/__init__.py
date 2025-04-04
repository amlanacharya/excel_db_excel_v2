"""
Processing phases for the Excel Processing System.
Provides classes for each phase of the Excel processing pipeline.
"""

from phase import Phase
from phase1_identification import DataIdentificationPhase
from phase2_storage import DataStoragePhase
from phase3_recreation import DataRecreationPhase
from phase4_correction import FontColorCorrectionPhase

__all__ = [
    'Phase',
    'DataIdentificationPhase',
    'DataStoragePhase',
    'DataRecreationPhase',
    'FontColorCorrectionPhase'
]