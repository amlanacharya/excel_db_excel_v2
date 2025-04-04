"""
Base Phase definition for the Excel Processing System.
Provides the interface that all processing phases must implement.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional

from core.context import ProcessingContext


class Phase(ABC):
    """
    Abstract base class for all processing phases.
    Enforces the interface that all phases must implement.
    """
    
    @abstractmethod
    def validate_prerequisites(self, context: ProcessingContext) -> bool:
        """
        Validate that all prerequisites for the phase are met.
        
        Args:
            context (ProcessingContext): The processing context
            
        Returns:
            bool: True if prerequisites are met, False otherwise
        """
        pass
    
    @abstractmethod
    def execute(self, context: ProcessingContext) -> bool:
        """
        Execute the phase.
        
        Args:
            context (ProcessingContext): The processing context
            
        Returns:
            bool: True if execution was successful, False otherwise
            
        Raises:
            PhaseExecutionError: If an error occurs during execution
        """
        pass