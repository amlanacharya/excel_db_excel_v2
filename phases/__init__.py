"""
Processing phases for the Excel Processing System.
Provides classes for each phase of the Excel processing pipeline.
"""

from excel_db_excel_v2.phases.phase import Phase
from excel_db_excel_v2.phases.phase1_identification import DataIdentificationPhase
from excel_db_excel_v2.phases.phase2_storage import DataStoragePhase
from excel_db_excel_v2.phases.phase3_recreation import DataRecreationPhase
from excel_db_excel_v2.phases.phase4_correction import FontColorCorrectionPhase

__all__ = [
    'Phase',
    'DataIdentificationPhase',
    'DataStoragePhase',
    'DataRecreationPhase',
    'FontColorCorrectionPhase'
]